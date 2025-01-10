import logging
from sherwood import errors
from sherwood.auth import generate_access_token, password_context
from sherwood.market_data_provider import MarketDataProvider
from sherwood.models import create_user, Holding, Ownership, Portfolio, User
from sqlalchemy.orm import Session
from sqlalchemy.exc import MultipleResultsFound

market_data_provider = MarketDataProvider()


def sign_up_user(db: Session, email: str, password: str) -> None:
    user = db.query(User).filter_by(email=email).first()
    if user is not None:
        raise errors.DuplicateUserError(email=email)
    try:
        user = create_user(db, email, password)
    except Exception as exc:
        raise errors.InternalServerError(detail="Failed to create user.") from exc


def sign_in_user(db: Session, email: str, password: str) -> str:
    try:
        user = db.query(User).filter_by(email=email).one_or_none()
    except MultipleResultsFound:
        raise errors.DuplicateUserError(email=email)
    if user is None:
        raise errors.MissingUserError(email=email)
    if not password_context.verify(password, user.password):
        raise errors.IncorrectPasswordError()
    if password_context.needs_update(user.password):
        user.password = password_context.hash(user.password)
    try:
        access_token = generate_access_token(user)
    except Exception as exc:
        msg = "Failed to generate access token."
        logging.error(f"{msg} User: {user}. Error: {exc}")
        raise errors.InternalServerError(msg)
    return access_token


def _lock_portfolios(db: Session, portfolio_ids: list[int]) -> dict[int, Portfolio]:
    if not portfolio_ids:
        raise ValueError("Must provide at least 1 portfolio to lock")
    condition = Portfolio.id == portfolio_ids[0]
    for portfolio_id in portfolio_ids[1:]:
        condition |= Portfolio.id == portfolio_id
    portfolios = db.query(Portfolio).filter(condition).with_for_update().all()
    portfolio_by_id = {portfolio.id: portfolio for portfolio in portfolios}
    if missing := set(portfolio_ids) - set(portfolio_by_id):
        raise errors.MissingPortfolioError(",".join(missing))
    return portfolio_by_id


def _try_db_commit(db, error_message: str):
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise errors.InternalServerError(f"{error_message} Error: {exc}") from exc


def deposit_cash_into_portfolio(db: Session, portfolio_id: int, dollars: float):
    portfolio = _lock_portfolios(db, [portfolio_id])[portfolio_id]
    portfolio.cash += dollars
    _try_db_commit(db, "Failed to deposit cash.")


def withdraw_cash_from_portfolio(db: Session, portfolio_id: int, dollars: float):
    portfolio = _lock_portfolios(db, [portfolio_id])[portfolio_id]
    if dollars > portfolio.cash:
        raise errors.InsufficientCashError(dollars, portfolio.cash)
    portfolio.cash -= dollars
    _try_db_commit(db, "Failed to withdraw cash.")


def _convert_dollars_to_units(symbol: str, dollars: float) -> float:
    return dollars / market_data_provider.get_price(symbol)


def buy_portfolio_holding(db: Session, portfolio_id, symbol: str, dollars: float):
    """Buys holding in owner's portfolio."""
    portfolio = _lock_portfolios(db, [portfolio_id])[portfolio_id]
    if dollars > portfolio.cash:
        raise errors.InsufficientCashError(needed=dollars, actual=portfolio.cash)
    holding = db.get(Holding, (portfolio_id, symbol))
    if holding is None:
        portfolio.holdings.append(Holding(portfolio_id, symbol, 0, 0))
        holding = portfolio.holdings[-1]
    ownership = db.get(Ownership, (portfolio_id, portfolio_id))
    if ownership is None:
        portfolio.ownership.append(Ownership(portfolio_id, portfolio_id, 0, 0))
        ownership = portfolio.ownership[-1]
    portfolio_value = sum(
        holding.units * market_data_provider.get_price(holding.symbol)
        for holding in portfolio.holdings
    )
    portfolio.cash -= dollars
    holding.units += _convert_dollars_to_units(symbol, dollars)
    holding.cost += dollars
    ownership.cost += dollars
    if portfolio_value > 0:
        percent = dollars / portfolio_value
        ownership.percent += percent
        for ownership in portfolio.ownership:
            ownership.percent /= 1 + percent
    else:
        ownership.percent = 1
    _try_db_commit(db, "Failed to buy holding.")


def sell_portfolio_holding(db: Session, portfolio_id: int, symbol: str, dollars: float):
    """Sells holding in owner's portfolio."""
    portfolio = _lock_portfolios(db, [portfolio_id])[portfolio_id]
    units = _convert_dollars_to_units(symbol, dollars)
    holding = db.get(Holding, (portfolio_id, symbol))
    if holding is None:
        raise errors.InsufficientHoldingsError(symbol, needed=units, actual=0)
    ownership = db.get(Ownership, (portfolio_id, portfolio_id))
    if ownership is None:
        raise errors.InternalServerError("Portfolio missing owner's ownership.")
    holding_by_symbol = {h.symbol: h for h in portfolio.holdings}
    holding_value_by_symbol = {
        s: h.units * market_data_provider.get_price(h.symbol)
        for s, h in holding_by_symbol.items()
    }
    if dollars > holding_value_by_symbol[symbol] * ownership.percent:
        raise errors.InsufficientHoldingsError(
            symbol,
            needed=units,
            actual=holding_by_symbol[symbol].units * ownership.percent,
        )
    holding.units -= units
    portfolio.cash += dollars
    holding.cost -= dollars
    ownership.cost -= dollars
    portfolio_value = sum(holding_value_by_symbol.values())
    if 0 < dollars < portfolio_value:
        percent = dollars / portfolio_value
        ownership.percent -= percent
        for ownership in portfolio.ownership:
            ownership.percent /= 1 - percent
    _try_db_commit(db, "Failed to sell holding.")


def invest_in_portfolio(
    db: Session, investee_portfolio_id: int, investor_portfolio_id: int, dollars: float
):
    if investee_portfolio_id == investor_portfolio_id:
        raise errors.RequestValueError("Self-invest prohibited")
    portfolio_by_id = _lock_portfolios(
        db, [investee_portfolio_id, investor_portfolio_id]
    )
    investor_portfolio = portfolio_by_id[investor_portfolio_id]
    if dollars > investor_portfolio.cash:
        raise errors.InsufficientCashError(dollars, investor_portfolio.cash)
    investee_portfolio = portfolio_by_id[investee_portfolio_id]
    investee_portfolio_ownership_by_owner_id = {
        ownership.owner_id: ownership for ownership in investee_portfolio.ownership
    }
    if investee_portfolio_id not in investee_portfolio_ownership_by_owner_id:
        raise errors.InternalServerError("Missing portfolio owner ownership info.")
    investee_portfolio_units_by_symbol = {
        holding.symbol: holding.units for holding in investee_portfolio.holdings
    }
    investee_portfolio_value_by_symbol = {
        symbol: units * market_data_provider.get_price(symbol)
        for symbol, units in investee_portfolio_units_by_symbol.items()
    }
    investee_portfolio_value = sum(investee_portfolio_value_by_symbol.values())
    if investee_portfolio_value < 0.01:
        raise errors.InsufficientHoldingsError(
            symbol=", ".join(list(investee_portfolio_units_by_symbol)),
            needed=0.01,
            actual=investee_portfolio_value,
        )
    investor_portfolio.cash -= dollars
    percent_increase = dollars / investee_portfolio_value
    for holding in investee_portfolio.holdings:
        holding.units += (
            investee_portfolio_units_by_symbol[holding.symbol] * percent_increase
        )
        holding.cost += (
            investee_portfolio_value_by_symbol[holding.symbol] * percent_increase
        )
    investor_ownership = investee_portfolio_ownership_by_owner_id.setdefault(
        investor_portfolio_id,
        Ownership(investee_portfolio_id, investor_portfolio_id, 0, 0),
    )
    investor_ownership.percent += percent_increase
    investor_ownership.cost += dollars
    denom = 1 + percent_increase
    for ownership in investee_portfolio_ownership_by_owner_id.values():
        ownership.percent /= denom
    investee_portfolio.ownership = list(
        investee_portfolio_ownership_by_owner_id.values()
    )
    _try_db_commit(db, "Failed to invest in portfolio.")


def divest_from_portfolio(
    db: Session, investee_portfolio_id: int, investor_portfolio_id: int, dollars: float
):
    pass

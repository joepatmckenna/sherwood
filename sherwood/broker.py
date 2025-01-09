import logging
from sherwood import errors
from sherwood.auth import generate_access_token, password_context
from sherwood.market_data_provider import MarketDataProvider
from sherwood.models import create_user, Holding, Ownership, Portfolio, User
from sqlalchemy.orm import joinedload, Session
from sqlalchemy.exc import NoResultFound, MultipleResultsFound

market_data_provider = MarketDataProvider()


def convert_dollars_to_units(symbol: str, dollars: float) -> float:
    return dollars / market_data_provider.get_price(symbol)


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


def _lock_portfolio_holdings_and_ownership(db: Session, portfolio_id: int):
    with db.begin_nested():
        try:
            portfolio = (
                db.query(Portfolio)
                .filter(Portfolio.id == portfolio_id)
                .with_for_update()
                .one()
            )
        except NoResultFound:
            raise errors.MissingPortfolioError(portfolio_id)
        except MultipleResultsFound:
            raise errors.DuplicatePortfolioError(portfolio_id)
        holdings = (
            db.query(Holding)
            .filter(Holding.portfolio_id == portfolio_id)
            .with_for_update()
            .all()
        )
        ownership = (
            db.query(Ownership)
            .filter(Ownership.portfolio_id == portfolio_id)
            .with_for_update()
            .all()
        )
        portfolio.holdings = holdings
        portfolio.ownership = ownership
        return portfolio


def _lock_portfolio(db: Session, portfolio_id: int):
    try:
        return (
            db.query(Portfolio).filter(Portfolio.id == portfolio_id).with_for_update()
        ).one()
    except NoResultFound:
        raise errors.MissingPortfolioError(portfolio_id)
    except MultipleResultsFound:
        raise errors.DuplicatePortfolioError(portfolio_id)


def deposit_cash_into_portfolio(db: Session, portfolio_id: int, dollars: float):
    portfolio = _lock_portfolio(db, portfolio_id)
    portfolio.cash += dollars
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise errors.InternalServerError(
            f"Failed to deposit cash. Error: {exc}"
        ) from exc


def withdraw_cash_from_portfolio(db: Session, portfolio_id: int, dollars: float):
    portfolio = _lock_portfolio(db, portfolio_id)
    if dollars > portfolio.cash:
        raise errors.InsufficientCashError(dollars, portfolio.cash)
    portfolio.cash -= dollars
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise errors.InternalServerError(
            f"Failed to withdraw cash. Error: {exc}"
        ) from exc


def buy_portfolio_holding(db: Session, portfolio_id, symbol: str, dollars: float):
    """Buys holding in owner's portfolio."""
    portfolio = _lock_portfolio_holdings_and_ownership(db, portfolio_id)

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
    holding.units += convert_dollars_to_units(symbol, dollars)
    holding.cost += dollars
    ownership.cost += dollars

    if portfolio_value > 0:
        percent = dollars / portfolio_value
        ownership.percent += percent
        for ownership in portfolio.ownership:
            ownership.percent /= 1 + percent
    else:
        ownership.percent = 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise errors.InternalServerError(
            f"Failed to buy holding. Error: {exc}"
        ) from exc


def sell_portfolio_holding(db: Session, portfolio_id: int, symbol: str, dollars: float):
    """Sells holding in owner's portfolio."""
    portfolio = _lock_portfolio_holdings_and_ownership(db, portfolio_id)

    units = convert_dollars_to_units(symbol, dollars)

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

    portfolio_value = sum(holding_value_by_symbol.values())
    if 0 < dollars < portfolio_value:
        percent = dollars / portfolio_value
        ownership.percent -= percent
        ownership.cost -= dollars
        for ownership in portfolio.ownership:
            ownership.percent /= 1 - percent
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise errors.InternalServerError(
            f"Failed to sell holding. Error: {exc}"
        ) from exc


def invest_in_portfolio(
    db: Session, portfolio_id: int, investor_id: int, dollars: float
):
    pass


def divest_from_portfolio(
    db: Session, portfolio_id: int, investor_id: int, dollars: float
):
    pass

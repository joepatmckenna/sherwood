from fastapi import status
import logging
from sherwood import errors
from sherwood.market_data_provider import MarketDataProvider
from sherwood.models import create_user, Holding, Ownership, Portfolio, User
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import NoResultFound, MultipleResultsFound, SQLAlchemyError
from sherwood.auth import generate_access_token, password_context

market_data_provider = MarketDataProvider()


def convert_dollars_to_units(symbol: str, dollars: float) -> float:
    return dollars / market_data_provider.get_price(symbol)


def sign_up_user(db, email, password) -> None:
    user = db.query(User).filter_by(email=email).first()
    if user is not None:
        raise errors.DuplicateUserError(email=email)
    try:
        user = create_user(db, email, password)
    except Exception as exc:
        raise errors.InternalServerError(detail="Failed to create user.") from exc


def sign_in_user(db, email, password) -> str:
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


def _get_locked_portfolio(db, portfolio_id):
    try:
        return (
            db.query(Portfolio)
            .options(
                joinedload(Portfolio.holdings),
                joinedload(Portfolio.ownership),
            )
            .filter(Portfolio.id == portfolio_id)
            .with_for_update()
        ).one()
    except NoResultFound:
        raise errors.MissingPortfolioError(portfolio_id)
    except MultipleResultsFound:
        raise errors.DuplicatePortfolioError(portfolio_id)


def buy_portfolio_holding(db, portfolio_id, symbol, dollars):
    """Buys holding in owner's portfolio.

    Need to lock:
    Portfolio(id==portfolio_id)
    all Holding(portfolio_id==portfolio_id)
    all Ownership(portfolio_id==portfolio_id)

    """
    with db.begin_nested():
        portfolio = _get_locked_portfolio(db, portfolio_id)

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


def sell_portfolio_holding(db, portfolio_id, symbol, dollars):
    if not dollars > 0:
        raise Exception()

    holding = db.get(Holding, (portfolio_id, symbol))
    if holding is None:
        raise Exception()  # TODO HoldingNotOwned

    ownership = db.get(Ownership, (portfolio_id, portfolio_id))
    if ownership is None:
        raise Exception()

    portfolio = db.get(Portfolio, portfolio_id)
    holding_value_by_symbol = {
        holding.symbol: holding.units * market_data_provider.get_price(holding.symbol)
        for holding in portfolio.holdings
    }

    if dollars > holding_value_by_symbol[symbol] * ownership.percent:
        raise Exception()

    portfolio.cash += dollars

    holding.units -= convert_dollars_to_units(symbol, dollars)
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
        logging.error(f"Error updating ownerships: {exc}")
        raise


def invest_in_portfolio(db, portfolio_id, investor_id, dollars):
    pass


def divest_from_portfolio(db, portfolio_id, investor_id, dollars):
    pass

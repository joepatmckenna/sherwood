from sherwood import errors
from sherwood.auth import generate_access_token, password_context
from sherwood.db import maybe_commit
from sherwood.errors import InternalServerError
from sherwood.market_data import get_price, get_prices
from sherwood.messages import (
    LeaderboardBlobRequest,
    LeaderboardBlobResponse,
    LeaderboardSortBy,
)
from sherwood.models import (
    create_user,
    to_dict,
    upsert_blob,
    Holding,
    Ownership,
    Portfolio,
    User,
)
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import MultipleResultsFound


STARTING_BALANCE = 100_000


def sign_up_user(
    db: Session,
    email: str,
    display_name: str,
    password: str,
    starting_balance=STARTING_BALANCE,
) -> None:
    if db.query(User).filter_by(email=email).first() is not None:
        raise errors.DuplicateUserError(email=email)
    if (
        db.query(User)
        .filter(func.lower(User.display_name) == display_name.lower())
        .first()
        is not None
    ):
        raise errors.DuplicateUserError(display_name=display_name)
    try:
        create_user(
            db=db,
            email=email,
            display_name=display_name,
            password=password,
            cash=starting_balance,
        )
    except Exception as exc:
        raise errors.InternalServerError(detail="Failed to create user.") from exc


def sign_in_user(
    db: Session,
    email: str,
    password: str,
    access_token_duration_hours: int = 4,
) -> str:
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
        access_token = generate_access_token(user, access_token_duration_hours)
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to generate access token. User: {user}. Error: {exc}"
        )
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
        raise errors.MissingPortfolioError(", ".join(map(str, missing)))
    return portfolio_by_id


def _convert_dollars_to_units(db, symbol: str, dollars: float) -> float:
    return dollars / get_price(db, symbol)


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
    price_by_symbol = get_prices(db, [holding.symbol for holding in portfolio.holdings])
    portfolio_value = sum(
        holding.units * price_by_symbol[holding.symbol]
        for holding in portfolio.holdings
    )
    portfolio.cash -= dollars
    holding.units += _convert_dollars_to_units(db, symbol, dollars)
    holding.cost += dollars
    ownership.cost += dollars
    if portfolio_value > 0:
        percent = dollars / portfolio_value
        ownership.percent += percent
        for ownership in portfolio.ownership:
            ownership.percent /= 1 + percent
    else:
        ownership.percent = 1
    maybe_commit(db, "Failed to buy holding.")


def sell_portfolio_holding(db: Session, portfolio_id: int, symbol: str, dollars: float):
    """Sells holding in owner's portfolio."""
    portfolio = _lock_portfolios(db, [portfolio_id])[portfolio_id]
    units = _convert_dollars_to_units(db, symbol, dollars)
    holding = db.get(Holding, (portfolio_id, symbol))
    if holding is None:
        raise errors.InsufficientHoldingsError(symbol, needed=units, actual=0)
    ownership = db.get(Ownership, (portfolio_id, portfolio_id))
    if ownership is None:
        raise errors.InternalServerError("Portfolio missing owner's ownership.")
    holding_by_symbol = {h.symbol: h for h in portfolio.holdings}
    price_by_symbol = get_prices(db, list(holding_by_symbol))
    holding_value_by_symbol = {
        s: h.units * price_by_symbol[h.symbol] for s, h in holding_by_symbol.items()
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
    maybe_commit(db, "Failed to sell holding.")


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
    price_by_symbol = get_prices(db, list(investee_portfolio_units_by_symbol))
    investee_portfolio_value_by_symbol = {
        symbol: units * price_by_symbol[symbol]
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
    maybe_commit(db, "Failed to invest in portfolio.")


def divest_from_portfolio(
    db: Session, investee_portfolio_id: int, investor_portfolio_id: int, dollars: float
):
    if investee_portfolio_id == investor_portfolio_id:
        raise errors.RequestValueError("Self-divest prohibited")
    portfolio_by_id = _lock_portfolios(
        db, [investee_portfolio_id, investor_portfolio_id]
    )
    investee_portfolio = portfolio_by_id[investee_portfolio_id]
    investee_portfolio_ownership_by_owner_id = {
        ownership.owner_id: ownership for ownership in investee_portfolio.ownership
    }
    if investor_portfolio_id not in investee_portfolio_ownership_by_owner_id:
        raise errors.InsufficientHoldingsError(
            symbol=f"Portfolio(id={investee_portfolio_id})", actual=0
        )
    investor_portfolio = portfolio_by_id[investor_portfolio_id]
    investee_portfolio_units_by_symbol = {
        holding.symbol: holding.units for holding in investee_portfolio.holdings
    }
    price_by_symbol = get_prices(db, list(investee_portfolio_units_by_symbol))
    investee_portfolio_value_by_symbol = {
        symbol: units * price_by_symbol[symbol]
        for symbol, units in investee_portfolio_units_by_symbol.items()
    }
    investee_portfolio_value = sum(investee_portfolio_value_by_symbol.values())
    percent_decrease = dollars / investee_portfolio_value
    if percent_decrease >= 1:
        raise errors.InternalServerError("Percent decrease >= 100%")
    if (
        percent_decrease
        > investee_portfolio_ownership_by_owner_id[investor_portfolio_id].percent
    ):
        raise errors.InsufficientHoldingsError(
            symbol=f"Portfolio(id={investee_portfolio_id})", actual=0
        )
    for holding in investee_portfolio.holdings:
        holding.units -= (
            investee_portfolio_units_by_symbol[holding.symbol] * percent_decrease
        )
    investor_portfolio.cash += dollars
    investor_ownership = investee_portfolio_ownership_by_owner_id[investor_portfolio_id]
    investor_ownership.percent -= percent_decrease
    investor_ownership.cost -= dollars
    denom = 1 - percent_decrease
    for ownership in investee_portfolio_ownership_by_owner_id.values():
        ownership.percent /= denom
    investee_portfolio.ownership = list(
        investee_portfolio_ownership_by_owner_id.values()
    )
    maybe_commit(db, "Failed to divest from portfolio.")


def enrich_user_with_price_info(db, user):
    user = to_dict(user)
    portfolio = user["portfolio"]
    user_ownership = [
        ownership
        for ownership in portfolio["ownership"]
        if ownership["owner_id"] == portfolio["id"]
    ]
    if not user_ownership:
        portfolio["gain_or_loss"] = 0
    else:
        user_ownership = user_ownership[0]
        portfolio["cost"] = portfolio["cash"]
        portfolio["value"] = portfolio["cash"]
        price_by_symbol = get_prices(
            db, [holding["symbol"] for holding in portfolio["holdings"]]
        )
        for holding in portfolio["holdings"]:
            holding["value"] = (
                user_ownership["percent"]
                * holding["units"]
                * price_by_symbol[holding["symbol"]]
            )
            holding["gain_or_loss"] = holding["value"] - holding["cost"]
            portfolio["cost"] += holding["cost"]
            portfolio["value"] += holding["value"]
        portfolio["gain_or_loss"] = portfolio["value"] - portfolio["cost"]
    user["portfolio"] = portfolio
    return user


def upsert_leaderboard(db, request: LeaderboardBlobRequest):
    key = repr(request)
    users = db.query(User).all()
    users = [enrich_user_with_price_info(db, user) for user in users]
    if request.sort_by == LeaderboardSortBy.GAIN_OR_LOSS:
        sort_fn = lambda user: user["portfolio"]["gain_or_loss"]
    else:
        raise InternalServerError(f"Unrecognized sort_by={request.sort_by}")
    users = sorted(users, key=sort_fn)[: request.top_k]
    response = LeaderboardBlobResponse(users=users)
    return upsert_blob(db, key, response.model_dump_json())


# def create_blob(db, request):
#     if isinstance(request, GetLeaderboardBlobRequest):
#         pass

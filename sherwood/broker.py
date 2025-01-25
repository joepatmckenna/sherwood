from sherwood.errors import (
    InsufficientCashError,
    InsufficientHoldingsError,
    InternalServerError,
    MissingHoldingError,
    MissingOwnershipError,
    MissingPortfolioError,
    RequestValueError,
)
from sherwood.db import maybe_commit
from sherwood.market_data import get_price, get_prices, DOLLAR_SYMBOL
from sherwood.models import Holding, Ownership, Portfolio
from sqlalchemy.orm import Session


_MIN_INVESTEE_PORTFOLIO_VALUE = 0.01
_MIN_INVESTOR_PORTFOLIO_OWNERSHIP_PERCENT = 0.01


# holding.cost: from owner's perspective
# holding.units: from fund's perspective
# ownership.cost: from investor's perspective
# ownership.percent: from fund's perspective

# invariant sum(holding.cost) = self_ownership.cost


def _lock_portfolios(db: Session, portfolio_ids: list[int]) -> dict[int, Portfolio]:
    if not portfolio_ids:
        raise ValueError("Must provide at least 1 portfolio to lock")
    condition = Portfolio.id == portfolio_ids[0]
    for portfolio_id in portfolio_ids[1:]:
        condition |= Portfolio.id == portfolio_id
    portfolios = db.query(Portfolio).filter(condition).with_for_update().all()
    portfolio_by_id = {portfolio.id: portfolio for portfolio in portfolios}
    if missing := set(portfolio_ids) - set(portfolio_by_id):
        raise MissingPortfolioError(", ".join(map(str, missing)))
    return portfolio_by_id


def _convert_dollars_to_units(db, symbol: str, dollars: float) -> float:
    return dollars / get_price(db, symbol)


def buy_portfolio_holding(db: Session, portfolio_id, symbol: str, dollars: float):
    """Buys holding in owner's portfolio."""
    portfolio = _lock_portfolios(db, [portfolio_id])[portfolio_id]
    self_ownership = db.get(Ownership, (portfolio_id, portfolio_id))
    if self_ownership is None:
        raise MissingOwnershipError(portfolio_id, portfolio_id)
    dollar_holding = db.get(Holding, (portfolio.id, DOLLAR_SYMBOL))
    if dollar_holding is None:
        raise MissingHoldingError(portfolio.id, DOLLAR_SYMBOL)
    if dollars > dollar_holding.units * self_ownership.percent:
        raise InsufficientCashError(
            needed=dollars, actual=dollar_holding.units * self_ownership.percent
        )
    holding = db.get(Holding, (portfolio_id, symbol))
    if holding is None:
        portfolio.holdings.append(Holding(portfolio_id, symbol, 0, 0))
        holding = portfolio.holdings[-1]
    dollar_holding.cost -= dollars
    holding.cost += dollars
    dollar_holding.units -= dollars / self_ownership.percent
    holding.units += _convert_dollars_to_units(
        db, symbol, dollars / self_ownership.percent
    )
    maybe_commit(db, "Failed to buy holding.")


def sell_portfolio_holding(db: Session, portfolio_id: int, symbol: str, dollars: float):
    """Sells holding in owner's portfolio."""
    portfolio = _lock_portfolios(db, [portfolio_id])[portfolio_id]
    holding = db.get(Holding, (portfolio_id, symbol))
    if holding is None:
        raise MissingHoldingError(portfolio_id, symbol)
    dollar_holding = db.get(Holding, (portfolio.id, DOLLAR_SYMBOL))
    if dollar_holding is None:
        raise MissingHoldingError(portfolio.id, DOLLAR_SYMBOL)
    self_ownership = db.get(Ownership, (portfolio_id, portfolio_id))
    if self_ownership is None:
        raise MissingOwnershipError(portfolio_id, portfolio_id)
    units = _convert_dollars_to_units(db, symbol, dollars)
    if units > holding.units * self_ownership.percent:
        raise InsufficientHoldingsError(
            symbol, needed=units / self_ownership.percent, actual=holding.units
        )
    holding.cost -= dollars
    dollar_holding.cost += dollars
    holding.units -= units / self_ownership.percent
    dollar_holding.units += dollars / self_ownership.percent
    maybe_commit(db, "Failed to sell holding.")


def invest_in_portfolio(
    db: Session, investee_portfolio_id: int, investor_portfolio_id: int, dollars: float
):
    """

    edge case to think about
    p2 holds 100% cash
    p1 invests in p2
    p2 invests all cash in p3

    """
    if investee_portfolio_id == investor_portfolio_id:
        raise RequestValueError("Self-invest prohibited")

    portfolio_by_id = _lock_portfolios(
        db, [investee_portfolio_id, investor_portfolio_id]
    )
    investee_portfolio = portfolio_by_id[investee_portfolio_id]
    investor_portfolio = portfolio_by_id[investor_portfolio_id]

    investor_dollar_holding = db.get(Holding, (investor_portfolio_id, DOLLAR_SYMBOL))
    if investor_dollar_holding is None:
        raise MissingHoldingError(investor_portfolio_id, DOLLAR_SYMBOL)
    investor_self_ownership = db.get(
        Ownership, (investor_portfolio_id, investor_portfolio_id)
    )
    if investor_self_ownership is None:
        raise MissingOwnershipError(investor_portfolio_id, investor_portfolio_id)
    if dollars > investor_dollar_holding.units * investor_self_ownership.percent:
        raise InsufficientCashError(
            dollars, investor_dollar_holding.units * investor_self_ownership.percent
        )

    investee_portfolio_owner_ids = set(
        ownership.owner_id for ownership in investee_portfolio.ownership
    )
    if investee_portfolio_id not in investee_portfolio_owner_ids:
        raise MissingOwnershipError(investee_portfolio_id, investee_portfolio_id)

    price_by_symbol = get_prices(
        db,
        [
            holding.symbol
            for holding in investee_portfolio.holdings + investor_portfolio.holdings
        ],
    )

    investee_portfolio_value = sum(
        holding.units * price_by_symbol[holding.symbol]
        for holding in investee_portfolio.holdings
    )
    if investee_portfolio_value < _MIN_INVESTEE_PORTFOLIO_VALUE:
        raise InternalServerError(
            f"Investee portfolio value < {_MIN_INVESTEE_PORTFOLIO_VALUE}"
        )
    investor_portfolio_value = sum(
        holding.units * price_by_symbol[holding.symbol]
        for holding in investor_portfolio.holdings
    )
    investee_portfolio_value_percent_increase = dollars / investee_portfolio_value
    investor_portfolio_value_percent_decrease = dollars / investor_portfolio_value

    if (investor_self_ownership.percent - investor_portfolio_value_percent_decrease) / (
        1 - investor_portfolio_value_percent_decrease
    ) < _MIN_INVESTOR_PORTFOLIO_OWNERSHIP_PERCENT:
        raise InternalServerError(
            f"Investor portfolio self-ownership would be <{100*_MIN_INVESTOR_PORTFOLIO_OWNERSHIP_PERCENT}%."
        )

    investor_dollar_holding.units -= dollars
    investor_dollar_holding.cost -= dollars
    for holding in investee_portfolio.holdings:
        holding.units *= 1 + investee_portfolio_value_percent_increase

    if investor_portfolio_id in investee_portfolio_owner_ids:
        is_investors = lambda ownership: ownership.owner_id == investor_portfolio_id
        investee_portfolio_investor_ownership = next(
            filter(is_investors, investee_portfolio.ownership)
        )
    else:
        ownership = Ownership(investee_portfolio_id, investor_portfolio_id, 0, 0)
        investee_portfolio.ownership.append(ownership)
        investee_portfolio_investor_ownership = investee_portfolio.ownership[-1]

    investee_portfolio_investor_ownership.cost += dollars
    investor_self_ownership.cost -= dollars

    investee_portfolio_investor_ownership.percent += (
        investee_portfolio_value_percent_increase
    )
    investor_self_ownership.percent -= investor_portfolio_value_percent_decrease

    for ownership in investee_portfolio.ownership:
        ownership.percent /= 1 + investee_portfolio_value_percent_increase

    for ownership in investor_portfolio.ownership:
        ownership.percent /= 1 - investor_portfolio_value_percent_decrease

    maybe_commit(db, "Failed to invest in portfolio.")


def divest_from_portfolio(
    db: Session, investee_portfolio_id: int, investor_portfolio_id: int, dollars: float
):
    if investee_portfolio_id == investor_portfolio_id:
        raise RequestValueError("Self-divest prohibited")
    investor_dollar_holding = db.get(Holding, (investor_portfolio_id, DOLLAR_SYMBOL))
    if investor_dollar_holding is None:
        raise MissingHoldingError(investor_portfolio_id, DOLLAR_SYMBOL)
    investor_portfolio_self_ownership = db.get(
        Ownership, (investor_portfolio_id, investor_portfolio_id)
    )
    if investor_portfolio_self_ownership is None:
        raise MissingOwnershipError(investor_portfolio_id, investor_portfolio_id)

    portfolio_by_id = _lock_portfolios(
        db, [investee_portfolio_id, investor_portfolio_id]
    )
    investee_portfolio = portfolio_by_id[investee_portfolio_id]
    investor_portfolio = portfolio_by_id[investor_portfolio_id]

    investee_portfolio_owner_ids = {
        ownership.owner_id for ownership in investee_portfolio.ownership
    }
    if investor_portfolio_id not in investee_portfolio_owner_ids:
        raise MissingOwnershipError(investee_portfolio_id, investor_portfolio_id)

    is_investors = lambda ownership: ownership.owner_id == investor_portfolio_id
    investee_portfolio_investor_ownership = next(
        filter(is_investors, investee_portfolio.ownership)
    )

    price_by_symbol = get_prices(
        db,
        [
            holding.symbol
            for holding in investee_portfolio.holdings + investor_portfolio.holdings
        ],
    )
    investee_portfolio_value = sum(
        holding.units * price_by_symbol[holding.symbol]
        for holding in investee_portfolio.holdings
    )
    investee_portfolio_investor_value = (
        investee_portfolio_value * investee_portfolio_investor_ownership.percent
    )
    if dollars > investee_portfolio_investor_value:
        # InsufficientValueError?
        raise InsufficientCashError(dollars, investee_portfolio_investor_value)
    investor_portfolio_value = sum(
        holding.units * price_by_symbol[holding.symbol]
        for holding in investor_portfolio.holdings
    )

    investee_portfolio_value_percent_decrease = dollars / investee_portfolio_value
    investor_portfolio_value_percent_increase = dollars / investor_portfolio_value

    for holding in investee_portfolio.holdings:
        holding.units *= 1 - investee_portfolio_value_percent_decrease

    investor_dollar_holding.units += dollars

    cost = (
        dollars
        / investee_portfolio_investor_value
        * investee_portfolio_investor_ownership.cost
    )
    investee_portfolio_investor_ownership.cost -= cost
    investor_portfolio_self_ownership.cost += cost
    investor_dollar_holding.cost += cost

    investee_portfolio_investor_ownership.percent -= (
        investee_portfolio_value_percent_decrease
    )
    for ownership in investee_portfolio.ownership:
        ownership.percent /= 1 - investee_portfolio_value_percent_decrease

    investor_portfolio_self_ownership.percent += (
        investor_portfolio_value_percent_increase
    )
    for ownership in investor_portfolio.ownership:
        ownership.percent /= 1 + investor_portfolio_value_percent_increase

    maybe_commit(db, "Failed to divest from portfolio.")

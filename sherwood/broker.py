import logging
from sherwood.models import Holding, Ownership, Portfolio, User
from sherwood.market_data_provider import MarketDataProvider

market_data_provider = MarketDataProvider()


def convert_dollars_to_units(symbol: str, dollars: float) -> float:
    return dollars / market_data_provider.get_price(symbol)


def buy_portfolio_holding(db, portfolio_id, symbol, dollars):
    if not dollars > 0:
        raise Exception()  # TODO ValueError

    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise Exception()  # TODO UserMissing

    if dollars > portfolio.cash:
        raise Exception()  # TODO InsufficientCashException
    portfolio.cash -= dollars

    holdings = db.query(Holding).filter_by(portfolio_id=portfolio_id).all()
    portfolio_value = sum(
        holding.units * market_data_provider.get_price(holding.symbol)
        for holding in holdings
    )

    holding = db.get(Holding, (portfolio_id, symbol))
    if holding is None:
        portfolio.holdings.append(Holding(portfolio_id, symbol, 0, 0))
        holding = portfolio.holdings[-1]

    ownership = db.get(Ownership, (portfolio_id, portfolio_id))
    if ownership is None:
        portfolio.ownership.append(Ownership(portfolio_id, portfolio_id, 0, 1))
        ownership = portfolio.ownership[-1]

    holding.cost += dollars

    holding.units += convert_dollars_to_units(symbol, dollars)

    ownership.cost += dollars

    if portfolio_value > 0:
        percent = dollars / portfolio_value
        ownership.percent += percent
        for ownership in portfolio.ownership:
            ownership.percent /= 1 + percent

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logging.error(f"Error updating ownerships: {exc}")
        raise


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

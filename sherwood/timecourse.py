from copy import copy

from sherwood.models import Holding, TransactionType
from sherwood.market_data import DOLLAR_SYMBOL
from sherwood.registrar import STARTING_BALANCE


def _extract_symbol_and_units(holding):
    return {"symbol": holding.symbol, "units": holding.units}


def reconstruct_holdings_history(portfolio):
    dollar_holding = Holding(
        portfolio.id,
        symbol=DOLLAR_SYMBOL,
        cost=STARTING_BALANCE,
        units=STARTING_BALANCE,
    )
    history = [
        {
            "timestamp": portfolio.created,
            "holdings": [_extract_symbol_and_units(dollar_holding)],
        }
    ]
    holding_by_symbol = {DOLLAR_SYMBOL: dollar_holding}
    for txn in portfolio.history:
        if txn.type == TransactionType.BUY:
            asset_holding = holding_by_symbol.setdefault(
                txn.asset, Holding(portfolio.id, txn.asset, 0, 0)
            )
            dollar_holding.cost -= txn.dollars
            dollar_holding.units -= txn.dollars
            asset_holding.cost += txn.dollars
            asset_holding.units += txn.dollars / txn.price
        elif txn.type == TransactionType.SELL:
            asset_holding = holding_by_symbol[txn.asset]
            units = txn.dollars / txn.price
            cost = units / asset_holding.units * asset_holding.cost
            asset_holding.units -= units
            asset_holding.cost -= cost
            dollar_holding.units += txn.dollars
            dollar_holding.cost += cost
        else:
            continue
        history.append(
            {
                "timestamp": txn.created,
                "holdings": list(
                    map(_extract_symbol_and_units, holding_by_symbol.values())
                ),
            }
        )
    return history

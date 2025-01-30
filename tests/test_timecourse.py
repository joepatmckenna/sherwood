from sherwood.broker import (
    buy_portfolio_holding,
    sell_portfolio_holding,
    invest_in_portfolio,
    divest_from_portfolio,
)
from sherwood.models import create_user
from sherwood.registrar import STARTING_BALANCE
from sherwood.timecourse import reconstruct_holdings_history


# python -m pytest tests/test_timecourse.py::test_reconstruct_holdings_history --capture=no


def test_reconstruct_holdings_history(
    db, valid_email, valid_display_name, valid_password
):
    user = create_user(
        db, valid_email, valid_display_name, valid_password, STARTING_BALANCE
    )
    buy_portfolio_holding(db, user.portfolio.id, "AAA", 50)
    buy_portfolio_holding(db, user.portfolio.id, "BBB", 200)
    buy_portfolio_holding(db, user.portfolio.id, "AAA", 50)
    history = reconstruct_holdings_history(user.portfolio)

    import json
    from sherwood.models import to_dict

    print(json.dumps(history, indent=2, default=str))


######


# request = StockBarsRequest(
#     symbol_or_symbols=[],
#     timeframe=TimeFrame.Day,
#     start=None,
#     end=None,
# )

# stock_historical_data_client.get_stock_bars(request)


######


# import urllib.parse
# from datetime import datetime, timezone
# from alpaca.data.historical import StockHistoricalDataClient
# from alpaca.data.models import BarSet
# from alpaca.data.requests import StockBarsRequest
# from alpaca.data.timeframe import TimeFrame
# def test_get_bars(reqmock, stock_client: StockHistoricalDataClient):
#     # Test single symbol request
#     symbol = "AAPL"
#     timeframe = TimeFrame.Day
#     start = datetime(2022, 2, 1)
#     limit = 2
#     _start_in_url = urllib.parse.quote_plus(
#         start.replace(tzinfo=timezone.utc).isoformat()
#     )
#     reqmock.get(
#         f"https://data.alpaca.markets/v2/stocks/bars?symbols=AAPL&start={_start_in_url}&timeframe={timeframe}&limit={limit}",
#         text="""
# {
#     "bars": {
#         "AAPL": [
#             {
#                 "t": "2022-02-01T05:00:00Z",
#                 "o": 174,
#                 "h": 174.84,
#                 "l": 172.31,
#                 "c": 174.61,
#                 "v": 85998033,
#                 "n": 732412,
#                 "vw": 173.703516
#             },
#             {
#                 "t": "2022-02-02T05:00:00Z",
#                 "o": 174.64,
#                 "h": 175.88,
#                 "l": 173.33,
#                 "c": 175.84,
#                 "v": 84817432,
#                 "n": 675034,
#                 "vw": 174.941288
#             }
#         ]
#     },
#     "next_page_token": "QUFQTHxEfDIwMjItMDItMDJUMDU6MDA6MDAuMDAwMDAwMDAwWg=="
# }
#         """,
#     )
#     request = StockBarsRequest(
#         symbol_or_symbols=symbol, timeframe=timeframe, start=start, limit=limit
#     )
#     barset = stock_client.get_stock_bars(request_params=request)
#     assert isinstance(barset, BarSet)
#     assert barset[symbol][0].open == 174
#     assert barset[symbol][0].high == 174.84
#     assert barset.df.index.nlevels == 2
#     assert reqmock.called_once

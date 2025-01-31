from alpaca.data import StockBarsRequest, TimeFrame
from alpaca.data.historical import StockHistoricalDataClient
from contextlib import contextmanager
from datetime import datetime
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import os
from sherwood.db import get_db, POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME, Session
from sherwood.errors import InternalServerError
from sherwood.models import BaseModel, TransactionType, User
from sherwood.market_data import DOLLAR_SYMBOL
from sherwood.registrar import STARTING_BALANCE
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


ALPACA_API_KEY_ENV_VAR_NAME = "ALPACA_API_KEY"
ALPACA_SECRET_KEY_ENV_VAR_NAME = "ALPACA_SECRET_KEY"


def _validate_env() -> None:
    if os.environ.get(POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME) is None:
        raise InternalServerError(
            f"Missing environment variable {POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME}"
        )
    if os.environ.get(ALPACA_API_KEY_ENV_VAR_NAME) is None:
        raise InternalServerError(
            f"Missing environment variable {ALPACA_API_KEY_ENV_VAR_NAME}"
        )
    if os.environ.get(ALPACA_SECRET_KEY_ENV_VAR_NAME) is None:
        raise InternalServerError(
            f"Missing environment variable {ALPACA_SECRET_KEY_ENV_VAR_NAME}"
        )


@contextmanager
def Database():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    load_dotenv(".env", override=True)

    _validate_env()

    postgresql_database_url = URL.create(
        drivername="postgresql",
        username="sherwood",
        password=os.environ.get(POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME),
        host="sql.joemckenna.xyz",
        port=5432,
        database="sherwood",
        query={"sslmode": "require"},
    )
    engine = create_engine(postgresql_database_url)
    Session.configure(bind=engine)

    BaseModel.metadata.create_all(engine)

    with Database() as db:
        user = db.get(User, 3)
        symbols = set(
            txn.asset
            for txn in user.portfolio.history
            if txn.type in {TransactionType.BUY, TransactionType.SELL}
        )

    if DOLLAR_SYMBOL in symbols:
        symbols.remove(DOLLAR_SYMBOL)

    symbols = list(symbols)

    transactions = list(
        filter(
            lambda txn: txn.type in {TransactionType.BUY, TransactionType.SELL},
            user.portfolio.history,
        )
    )

    stock_historical_data_client = StockHistoricalDataClient(
        api_key=os.environ.get(ALPACA_API_KEY_ENV_VAR_NAME),
        secret_key=os.environ.get(ALPACA_SECRET_KEY_ENV_VAR_NAME),
    )

    start = user.portfolio.created
    end = datetime.now()

    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Hour,
        start=start,
        end=end,
    )

    bars = stock_historical_data_client.get_stock_bars(request)

    timestamps = bars.df.index.get_level_values(1).unique().sort_values()

    prices = {DOLLAR_SYMBOL: 1}
    units = {DOLLAR_SYMBOL: STARTING_BALANCE}

    i_txn = 0
    timecourse = []
    for timestamp in timestamps:
        prices.update(bars.df.xs(timestamp, level="timestamp")["open"].to_dict())

        if i_txn < len(transactions) and transactions[
            i_txn
        ].created < timestamp.replace(tzinfo=None):
            txn = transactions[i_txn]
            i_txn += 1
            if txn.type == TransactionType.BUY:
                units[DOLLAR_SYMBOL] -= txn.dollars
                units.setdefault(txn.asset, 0)
                units[txn.asset] += txn.dollars / txn.price
            elif txn.type == TransactionType.SELL:
                units[txn.asset] -= txn.dollars / txn.price
                units[DOLLAR_SYMBOL] += txn.dollars

        if any(s not in prices for s, n in units.items() if n > 0):
            print("missing prices", timestamp, units, prices)
            continue

        timecourse.append(
            {
                "timestamp": timestamp,
                "value": sum(prices[s] * n for s, n in units.items()),
            }
        )

    fig = plt.figure()
    ax = plt.gca()
    t = [x["timestamp"] for x in timecourse]
    y = [x["value"] for x in timecourse]
    ax.plot(t, y)
    ax.scatter(t, y)
    plt.show()
    plt.close()

    for x in timecourse:
        print(x)

    engine.dispose()

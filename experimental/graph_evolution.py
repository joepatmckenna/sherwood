from alpaca.data import StockHistoricalDataClient, StockQuotesRequest
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import cache
import matplotlib.animation as animation
from matplotlib.patches import Wedge
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import os
import pickle
from sherwood.db import get_db, POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME, Session
from sherwood.errors import InternalServerError
from sherwood.models import BaseModel, Transaction, TransactionType, User
from sherwood.market_data import DOLLAR_SYMBOL
from sherwood.registrar import STARTING_BALANCE
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from tqdm import tqdm

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


@cache
def get_symbol_color(symbol):
    if symbol == DOLLAR_SYMBOL:
        return "white"
    return np.random.rand(3)


if __name__ == "__main__":
    load_dotenv(".env", override=True)
    _validate_env()

    stock_historical_data_client = StockHistoricalDataClient(
        api_key=os.environ.get(ALPACA_API_KEY_ENV_VAR_NAME),
        secret_key=os.environ.get(ALPACA_SECRET_KEY_ENV_VAR_NAME),
    )

    if os.path.exists("prices.pkl"):
        with open("prices.pkl", "rb") as f:
            _prices = pickle.load(f)
    else:
        _prices = {}

    def get_price(symbol, timestamp):
        if symbol == DOLLAR_SYMBOL:
            return 1
        key = (symbol, timestamp)
        if key in _prices:
            return _prices[key]
        raise ValueError()
        request = StockQuotesRequest(symbol_or_symbols=symbol, start=timestamp, limit=1)
        response = stock_historical_data_client.get_stock_quotes(request)
        quote = response[symbol][0]
        price = 0.5 * (quote.bid_price + quote.ask_price)
        _prices[key] = price
        return price

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

    fig = plt.figure(figsize=(8, 8))
    ax = plt.gca()
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    plt.tight_layout()

    G = nx.Graph()

    with Database() as db:
        users = db.query(User).all()
        transactions = db.query(Transaction).all()

        user_by_timestamp = {user.created: user for user in users}
        transaction_by_timestamp = {
            transaction.created: transaction for transaction in transactions
        }
        user_id_by_display_name = {user.display_name: user.id for user in users}

        data_by_user_id = {
            user.id: {
                "holdings": {
                    DOLLAR_SYMBOL: {
                        "units": STARTING_BALANCE,
                        "cost": STARTING_BALANCE,
                        "value": STARTING_BALANCE,
                    },
                },
                "ownership": {
                    user.id: 1.0,
                },
            }
            for user in users
        }

        user_timestamps = deque(sorted(user_by_timestamp))
        transaction_timestamps = deque(sorted(transaction_by_timestamp))

        min_t = user_timestamps[0]
        max_t = transaction_timestamps[-1]

        frames = 10_000
        pos = {}
        next_pos = {}
        s = 1

        def spawn():
            o = np.pi / 2
            r = 1
            while True:
                x = r * np.cos(o)
                y = r * np.sin(o)
                yield np.array([x, y])
                o -= np.pi / 4

        loc = spawn()

        def draw_pie_chart(ax, center, data):
            start_angle = 90

            holdings_value = sum(h["value"] for h in data["holdings"].values())
            max_radius = holdings_value / STARTING_BALANCE * 0.1

            factor = 360 / sum(
                holding["value"] for holding in data["holdings"].values()
            )

            start_radius = 0
            for percent in data["ownership"].values():
                radius = start_radius + percent * max_radius + 0.01
                for symbol, holding in data["holdings"].items():
                    angle = holding["value"] * factor
                    ax.add_patch(
                        Wedge(
                            center,
                            radius,
                            start_angle,
                            start_angle + angle,
                            width=percent * max_radius,
                            facecolor=get_symbol_color(symbol),
                            edgecolor="black",
                            linewidth=0.2,
                            antialiased=True,
                        )
                    )
                    start_angle += angle
                start_radius = radius

        def update(i):
            global pos, next_pos, s

            t = min_t + i * (max_t - min_t) / frames

            while user_timestamps and t >= user_timestamps[0]:
                timestamp = user_timestamps.popleft()
                user = user_by_timestamp[timestamp]
                G.add_node(user.id)
                pos[user.id] = next(loc)
                fixed = list(set(pos) - {user.id})
                next_pos = nx.spring_layout(
                    G, pos=pos, iterations=4, fixed=fixed or None, seed=42
                )
                s = 1

            while transaction_timestamps and t >= transaction_timestamps[0]:
                timestamp = transaction_timestamps.popleft()
                transaction = transaction_by_timestamp[timestamp]
                if transaction.type == TransactionType.BUY:
                    for key in ["units", "cost", "value"]:
                        data_by_user_id[transaction.portfolio_id]["holdings"][
                            DOLLAR_SYMBOL
                        ][key] -= transaction.dollars
                    data_by_user_id[transaction.portfolio_id]["holdings"].setdefault(
                        transaction.asset, {"units": 0, "cost": 0, "value": 0}
                    )
                    data_by_user_id[transaction.portfolio_id]["holdings"][
                        transaction.asset
                    ]["units"] += (transaction.dollars / transaction.price)
                    data_by_user_id[transaction.portfolio_id]["holdings"][
                        transaction.asset
                    ]["cost"] += transaction.dollars
                    data_by_user_id[transaction.portfolio_id]["holdings"][
                        transaction.asset
                    ]["value"] += transaction.dollars
                elif transaction.type == TransactionType.INVEST:
                    src = transaction.portfolio_id
                    dst = user_id_by_display_name[transaction.asset]

                    for id in [src, dst]:
                        for symbol, holding in data_by_user_id[id]["holdings"].items():
                            data_by_user_id[id]["holdings"][symbol]["value"] = holding[
                                "units"
                            ] * get_price(symbol, transaction.created)

                    src_value = sum(
                        h["value"] for h in data_by_user_id[src]["holdings"].values()
                    )
                    dst_value = sum(
                        h["value"] for h in data_by_user_id[dst]["holdings"].values()
                    )

                    percent_decrease = transaction.dollars / src_value
                    percent_increase = transaction.dollars / dst_value

                    data_by_user_id[src]["ownership"][src] -= percent_decrease
                    data_by_user_id[dst]["ownership"].setdefault(src, 0)
                    data_by_user_id[dst]["ownership"][src] += percent_increase

                    # < 1
                    shrink_factor = sum(data_by_user_id[src]["ownership"].values())
                    # > 1
                    growth_factor = sum(data_by_user_id[dst]["ownership"].values())

                    for key in ["units", "cost", "value"]:
                        data_by_user_id[src]["holdings"][DOLLAR_SYMBOL][
                            key
                        ] -= transaction.dollars
                    for symbol in data_by_user_id[dst]["holdings"].keys():
                        for key in ["units", "value"]:
                            data_by_user_id[dst]["holdings"][symbol][
                                key
                            ] *= growth_factor

                    for id in data_by_user_id[src]["ownership"].keys():
                        data_by_user_id[src]["ownership"][id] /= shrink_factor
                    for id in data_by_user_id[dst]["ownership"].keys():
                        data_by_user_id[dst]["ownership"][id] /= growth_factor

                    G.add_edge(src, dst, weight=1.0 / transaction.dollars)
                    fixed = list(set(pos) - {src, dst})
                    next_pos = nx.spring_layout(
                        G, pos=pos, iterations=4, fixed=fixed or None, seed=42
                    )
                    s = 1

            pos = {i: x + (1 - s) * (next_pos.get(i, x) - x) for i, x in pos.items()}
            s *= 0.9

            ax.clear()
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])

            x, y = list(zip(*pos.values()))
            xmin, xmax = min(x), max(x)
            ymin, ymax = min(y), max(y)
            lim = max(abs(xmin), abs(xmax), abs(ymin), abs(ymax)) * 1.2
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)

            nx.draw_networkx_edges(G, pos=pos, ax=ax, edge_color="k")
            for node in G.nodes():
                draw_pie_chart(ax, pos[node], data_by_user_id[node])

        ani = animation.FuncAnimation(
            fig, update, frames=frames, interval=100, repeat=False
        )
        # plt.show()

        with open("prices.pkl", "wb") as f:
            pickle.dump(_prices, f)

        with tqdm(total=frames) as pbar:
            ani.save(
                "network_evolution.mp4",
                writer=animation.FFMpegWriter(fps=240, metadata={"artist": "NetworkX"}),
                progress_callback=lambda i, n: pbar.update(1),
            )

        print(data_by_user_id)

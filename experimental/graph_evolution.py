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
        # raise ValueError()
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
        display_name_by_user_id = {v: k for k, v in user_id_by_display_name.items()}

        data_by_user_id = {
            user.id: {
                "cash": STARTING_BALANCE,
                "holdings": {},
                "ownership": {user.id: {"percent": 1, "cost": 0}},
            }
            for user in users
        }

        user_timestamps = deque(sorted(user_by_timestamp))
        transaction_timestamps = deque(sorted(transaction_by_timestamp))

        min_t = user_timestamps[0]
        max_t = transaction_timestamps[-1]

        frames = 1_000
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

        def draw_pie_chart(ax, center, data, user_id):
            start_angle = 90

            total_value = sum(
                h["value"] for h in data["holdings"].values()
            )  #  + data["cash"]
            max_radius = total_value / STARTING_BALANCE * 0.1

            label_x = center[0]
            label_y = center[1] + (max_radius + 0.03)

            ax.text(
                label_x,
                label_y,
                display_name_by_user_id[user_id],
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
            )

            if total_value == 0:
                return

            factor = 360 / total_value

            start_radius = 0
            for id in sorted(data["ownership"], key=lambda id: abs(id - user_id)):
                percent = data["ownership"][id]["percent"]
                radius = start_radius + percent * max_radius + 0.01
                # angle = data["cash"] * factor
                # ax.add_patch(
                #     Wedge(
                #         center,
                #         radius,
                #         start_angle,
                #         start_angle + angle,
                #         width=percent * max_radius,
                #         facecolor="white",
                #         edgecolor="black",
                #         linewidth=0.2,
                #         antialiased=True,
                #     )
                # )
                # start_angle += angle
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
                    G, pos=pos, iterations=2, fixed=fixed or None, seed=42
                )
                s = 1

            while transaction_timestamps and t >= transaction_timestamps[0]:
                timestamp = transaction_timestamps.popleft()
                transaction = transaction_by_timestamp[timestamp]
                if transaction.type == TransactionType.BUY:
                    data_by_user_id[transaction.portfolio_id][
                        "cash"
                    ] -= transaction.dollars
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
                    data_by_user_id[transaction.portfolio_id]["ownership"][
                        transaction.portfolio_id
                    ]["cost"] += transaction.dollars
                    for symbol, holding in data_by_user_id[transaction.portfolio_id][
                        "holdings"
                    ].items():
                        data_by_user_id[transaction.portfolio_id]["holdings"][symbol][
                            "value"
                        ] = holding["units"] * get_price(symbol, transaction.created)
                    value = sum(
                        h["value"]
                        for h in data_by_user_id[transaction.portfolio_id][
                            "holdings"
                        ].values()
                    )
                    percent_increase = transaction.dollars / value
                    data_by_user_id[transaction.portfolio_id]["ownership"][
                        transaction.portfolio_id
                    ]["percent"] += percent_increase
                    for id in data_by_user_id[transaction.portfolio_id]["ownership"]:
                        data_by_user_id[transaction.portfolio_id]["ownership"][id][
                            "percent"
                        ] /= (1 + percent_increase)

                elif transaction.type == TransactionType.INVEST:
                    src = transaction.portfolio_id
                    dst = user_id_by_display_name[transaction.asset]

                    for symbol, holding in data_by_user_id[dst]["holdings"].items():
                        data_by_user_id[dst]["holdings"][symbol]["value"] = holding[
                            "units"
                        ] * get_price(symbol, transaction.created)

                    dst_value = sum(
                        h["value"] for h in data_by_user_id[dst]["holdings"].values()
                    )

                    percent_increase = transaction.dollars / dst_value

                    data_by_user_id[src]["cash"] -= transaction.dollars

                    data_by_user_id[dst]["ownership"].setdefault(
                        src, {"percent": 0, "cost": 0}
                    )
                    data_by_user_id[dst]["ownership"][src][
                        "cost"
                    ] += transaction.dollars
                    data_by_user_id[dst]["ownership"][src][
                        "percent"
                    ] += percent_increase

                    # > 1
                    growth_factor = sum(
                        o["percent"] for o in data_by_user_id[dst]["ownership"].values()
                    )

                    for symbol in data_by_user_id[dst]["holdings"].keys():
                        for key in ["units", "value"]:
                            data_by_user_id[dst]["holdings"][symbol][
                                key
                            ] *= growth_factor

                    for id in data_by_user_id[dst]["ownership"].keys():
                        data_by_user_id[dst]["ownership"][id][
                            "percent"
                        ] /= growth_factor

                    G.add_edge(src, dst, weight=transaction.dollars / STARTING_BALANCE)
                    fixed = list(set(pos) - {src, dst})
                    next_pos = nx.spring_layout(
                        G, pos=pos, iterations=2, fixed=fixed or None, seed=42
                    )
                    s = 1

            pos = {i: x + (1 - s) * (next_pos.get(i, x) - x) for i, x in pos.items()}
            s *= 0.95

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
                draw_pie_chart(ax, pos[node], data_by_user_id[node], node)

        ani = animation.FuncAnimation(
            fig, update, frames=frames, interval=100, repeat=False
        )
        # plt.show()

        with open("prices.pkl", "wb") as f:
            pickle.dump(_prices, f)

        with tqdm(total=frames) as pbar:
            ani.save(
                "network_evolution.mp4",
                writer=animation.FFMpegWriter(fps=60, metadata={"artist": "NetworkX"}),
                progress_callback=lambda i, n: pbar.update(1),
            )

        print(data_by_user_id)

{
    3: {
        "cash": 2997.0,
        "holdings": {
            "COST": {
                "units": 5.303957300138257,
                "cost": 1000.0,
                "value": 5210.978928666834,
            },
            "HOOD": {
                "units": 107.240150480906,
                "cost": 1000.0,
                "value": 5610.804673161002,
            },
            "VOO": {
                "units": 1.7977135890682663,
                "cost": 1001.0,
                "value": 998.6928187030393,
            },
        },
        "ownership": {
            3: {"percent": 0.19838184922564825, "cost": 3001.0},
            7: {"percent": 0.3685716248519146, "cost": 2500.0},
            6: {"percent": 0.43304652592243714, "cost": 5000.0},
        },
    },
    4: {
        "cash": 9300.0,
        "holdings": {
            "TSLA": {
                "units": 1.7488372950642093,
                "cost": 100.0,
                "value": 698.7217086834788,
            },
            "GOOG": {
                "units": 3.584407966840845,
                "cost": 100.0,
                "value": 709.8740757929952,
            },
            "AAPL": {
                "units": 3.021625040175544,
                "cost": 100.0,
                "value": 720.8237614590769,
            },
            "MSFT": {
                "units": 1.5982850049124415,
                "cost": 100.0,
                "value": 694.5107746096277,
            },
            "AMZN": {
                "units": 2.950262219585212,
                "cost": 100.0,
                "value": 699.0646329307159,
            },
            "META": {
                "units": 0.30773309350176137,
                "cost": 100.0,
                "value": 217.64576904458826,
            },
            "NVDA": {
                "units": 1.7148025142707508,
                "cost": 100.0,
                "value": 217.79706733752806,
            },
        },
        "ownership": {
            4: {"percent": 0.1626830438751471, "cost": 700.0},
            3: {"percent": 0.32976547054933963, "cost": 1002.0},
            5: {"percent": 0.12861411693903285, "cost": 500.0},
            6: {"percent": 0.3789373686364805, "cost": 1500.0},
        },
    },
    5: {
        "cash": 7500.0,
        "holdings": {
            "NVDA": {
                "units": 85.64513633789974,
                "cost": 2000.0,
                "value": 10894.061342180848,
            }
        },
        "ownership": {
            5: {"percent": 0.09737171908108887, "cost": 2000.0},
            7: {"percent": 0.7195800794583509, "cost": 4000.0},
            3: {"percent": 0.09125507045182546, "cost": 1000.0},
            6: {"percent": 0.0917931310087348, "cost": 1000.0},
        },
    },
    6: {
        "cash": 400.0,
        "holdings": {
            "GOOG": {
                "units": 5.9305869754268885,
                "cost": 1000.0,
                "value": 1173.6928153718584,
            },
            "VOO": {
                "units": 2.086646759682312,
                "cost": 1000.0,
                "value": 1160.8746250478591,
            },
        },
        "ownership": {
            6: {"percent": 0.5716551243342038, "cost": 2000.0},
            3: {"percent": 0.42834487566579627, "cost": 1000.0},
        },
    },
    7: {
        "cash": 655.0,
        "holdings": {
            "AAPL": {
                "units": 1.1241075684836006,
                "cost": 200.0,
                "value": 268.31323552135063,
            },
            "PLTR": {
                "units": 5.35793269566719,
                "cost": 321.0,
                "value": 427.9916637298952,
            },
            "SPY": {
                "units": 2.2024060886439703,
                "cost": 1000.0,
                "value": 1328.0288473914277,
            },
            "SCHD": {
                "units": 63.187232164892926,
                "cost": 1324.0,
                "value": 1769.242500617002,
            },
        },
        "ownership": {
            7: {"percent": 0.7106630938353992, "cost": 2845.0},
            3: {"percent": 0.26297655553971583, "cost": 1000.0},
            6: {"percent": 0.026360350624884874, "cost": 100.0},
        },
    },
    8: {"cash": 10000, "holdings": {}, "ownership": {8: {"percent": 0, "cost": 0}}},
}

from collections import deque
from contextlib import contextmanager
from datetime import datetime, timedelta
from dotenv import load_dotenv
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import os
from sherwood.db import get_db, POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME, Session
from sherwood.errors import InternalServerError
from sherwood.models import BaseModel, Transaction, TransactionType, User
from sherwood.market_data import DOLLAR_SYMBOL
from sherwood.registrar import STARTING_BALANCE
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from tqdm import tqdm


def _validate_env() -> None:
    if os.environ.get(POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME) is None:
        raise InternalServerError(
            f"Missing environment variable {POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME}"
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

    fig, ax = plt.subplots()
    ax.set_xticks([])
    ax.set_yticks([])

    G = nx.Graph()

    with Database() as db:
        users = db.query(User).all()
        transactions = db.query(Transaction).all()

        user_id_by_display_name = {user.display_name: user.id for user in users}

        user_by_timestamp = {user.created: user for user in users}
        transaction_by_timestamp = {
            transaction.created: transaction for transaction in transactions
        }

        user_timestamps = deque(sorted(user_by_timestamp))
        transaction_timestamps = deque(sorted(transaction_by_timestamp))

        min_t = user_timestamps[0]
        max_t = transaction_timestamps[-1]

        frames = 1000
        pos = {}
        next_pos = {}
        s = 1

        def spawn():
            o = 0
            while True:
                x = np.cos(o)
                y = np.sin(o)
                yield x, y
                o -= np.pi / 16

        loc = spawn()

        def update(i):
            global pos, next_pos, s

            t = min_t + i * (max_t - min_t) / frames

            while user_timestamps and t >= user_timestamps[0]:
                timestamp = user_timestamps.popleft()
                user = user_by_timestamp[timestamp]
                G.add_node(user.id)
                pos[user.id] = next(loc)
                next_pos = nx.spring_layout(G, pos=pos, iterations=4, seed=0)
                s = 1

            while transaction_timestamps and t >= transaction_timestamps[0]:
                timestamp = transaction_timestamps.popleft()
                transaction = transaction_by_timestamp[timestamp]

                if transaction.type == TransactionType.INVEST:
                    G.add_edge(
                        transaction.portfolio_id,
                        user_id_by_display_name[transaction.asset],
                    )
                    next_pos = nx.spring_layout(G, pos=pos, iterations=4, seed=0)
                    s = 1

            ax.clear()
            ax.set_xticks([])
            ax.set_yticks([])

            pos = {i: x + (1 - s) * (next_pos.get(i, x) - x) for i, x in pos.items()}
            s *= 0.999

            nx.draw(G, pos, ax, node_color="black", edge_color="gray", node_size=100)

        ani = animation.FuncAnimation(
            fig, update, frames=frames, interval=100, repeat=False
        )

        writer = animation.FFMpegWriter(fps=60, metadata={"artist": "NetworkX"})
        with tqdm(total=frames) as pbar:
            ani.save(
                "network_evolution.mp4",
                writer=writer,
                progress_callback=lambda i, n: pbar.update(1),
            )

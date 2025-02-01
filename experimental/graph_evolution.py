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

    # for user in users:
    #     pos[user.id] = np.zeros(2)
    #     print(pos)
    #     for _ in range(10):

    # fig, ax = plt.subplots()
    # ax.set_xticks([])
    # ax.set_yticks([])

    # nx.draw(
    #     G,
    #     pos,
    #     with_labels=True,
    #     node_color="lightblue",
    #     edge_color="gray",
    #     node_size=500,
    #     ax=ax,
    # )


# import matplotlib.pyplot as plt
# import matplotlib.animation as animation
# import numpy as np

# # Define the number of users (nodes) and edges
# num_users = 20  # Change as needed
# edges = [(np.random.randint(0, i), i) for i in range(1, num_users)]  # Tree-like growth

# # Initialize graph
# G = nx.Graph()
# pos = {}  # Store positions of nodes

# # Set up figure
# fig, ax = plt.subplots()
# ax.set_xticks([])
# ax.set_yticks([])

# # Function to update the animation
# def update(num):
#     global pos
#     ax.clear()
#     ax.set_xticks([])
#     ax.set_yticks([])

#     # Add the next node and edge
#     if num < len(edges):
#         G.add_edge(*edges[num])

#     # Ensure pos is initialized correctly
#     if not pos:  # First node case
#         first_node = list(G.nodes)[0]
#         pos = {first_node: np.array([0, 0])}  # Place first node at origin

#     if len(G.nodes) > 1:
#         # Run spring layout with the previous positions as a starting point
#         pos = nx.spring_layout(G, pos=pos if len(pos) > 0 else None, iterations=10, seed=42)

#     # Draw network
#     nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray', node_size=500, ax=ax)
#     ax.set_title(f"Network Evolution: {num+1} Users")

# # Create animation
# ani = animation.FuncAnimation(fig, update, frames=len(edges), interval=500, repeat=False)

# plt.show()

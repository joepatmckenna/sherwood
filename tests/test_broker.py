from pytest import approx
from sherwood.broker import (
    buy_portfolio_holding,
    sell_portfolio_holding,
    invest_in_portfolio,
    divest_from_portfolio,
)
from sherwood.models import create_user, User, Portfolio, Holding, Ownership


def test_buy_portfolio_holding(db, valid_email, valid_display_name, valid_password):
    expected = User(
        email="user@web.com",
        display_name="user",
        password=valid_password,
    )
    expected.id = 1
    expected.portfolio = Portfolio(
        id=1,
        holdings=[
            Holding(portfolio_id=1, symbol="AAA", cost=100.0, units=100.0),
            Holding(portfolio_id=1, symbol="BBB", cost=200.0, units=100.0),
            Holding(portfolio_id=1, symbol="USD", cost=700.0, units=700.0),
        ],
        ownership=[Ownership(portfolio_id=1, owner_id=1, cost=1000.0, percent=1.0)],
    )
    expected.portfolio.id = 1
    user = create_user(db, valid_email, valid_display_name, valid_password, 1000)
    buy_portfolio_holding(db, user.portfolio.id, "AAA", 50)
    buy_portfolio_holding(db, user.portfolio.id, "BBB", 200)
    buy_portfolio_holding(db, user.portfolio.id, "AAA", 50)
    assert expected == db.get(User, 1)


def test_sell_portfolio_holding(db, valid_email, valid_display_name, valid_password):
    expected = User(
        email=valid_email, display_name=valid_display_name, password=valid_password
    )
    expected.id = 1
    expected.portfolio = Portfolio(
        id=1,
        holdings=[
            Holding(portfolio_id=1, symbol="AAA", cost=50, units=50),
            Holding(portfolio_id=1, symbol="BBB", cost=100, units=50),
            Holding(portfolio_id=1, symbol="USD", cost=850, units=850),
        ],
        ownership=[
            Ownership(portfolio_id=1, owner_id=1, cost=1000, percent=1),
        ],
    )
    expected.portfolio.id = 1

    user = create_user(
        db, valid_email, valid_display_name, valid_password, starting_balance=1000
    )
    buy_portfolio_holding(db, user.portfolio.id, "AAA", 100)
    buy_portfolio_holding(db, user.portfolio.id, "BBB", 200)
    sell_portfolio_holding(db, user.portfolio.id, "AAA", 50)
    sell_portfolio_holding(db, user.portfolio.id, "BBB", 100)

    assert expected == db.get(User, 1)


def test_buy_and_sell_cancel(db, valid_email, valid_display_name, valid_password):
    expected = User(
        email=valid_email, display_name=valid_display_name, password=valid_password
    )
    expected.id = 1
    expected.portfolio = Portfolio(
        id=1,
        holdings=[
            Holding(portfolio_id=1, symbol="BBB", cost=0, units=0),
            Holding(portfolio_id=1, symbol="USD", cost=1000, units=1000),
        ],
        ownership=[
            Ownership(portfolio_id=1, owner_id=1, cost=1000, percent=1),
        ],
    )
    expected.portfolio.id = 1

    user = create_user(
        db, valid_email, valid_display_name, valid_password, starting_balance=1000
    )
    buy_portfolio_holding(db, user.portfolio.id, "BBB", 200)
    sell_portfolio_holding(db, user.portfolio.id, "BBB", 200)
    assert user == expected


# python -m pytest tests/test_broker.py::test_invest_in_portfolio_success --capture=no


def test_invest_in_portfolio_success(
    db, valid_emails, valid_display_names, valid_password
):
    expected = [
        User(email="user0@web.com", display_name="user0", password=valid_password),
        User(email="user1@web.com", display_name="user1", password=valid_password),
    ]
    expected[0].id = 1
    expected[0].portfolio = Portfolio(
        id=1,
        holdings=[
            Holding(portfolio_id=1, symbol="AAA", cost=90.0, units=90.9),
            Holding(portfolio_id=1, symbol="USD", cost=910.0, units=919.1),
        ],
        ownership=[
            Ownership(portfolio_id=1, owner_id=1, cost=1000.0, percent=1000 / 1010),
            Ownership(portfolio_id=1, owner_id=2, cost=10.0, percent=10 / 1010),
        ],
    )
    expected[1].id = 2
    expected[1].portfolio = Portfolio(
        id=2,
        holdings=[Holding(portfolio_id=2, symbol="USD", cost=990, units=990)],
        ownership=[Ownership(portfolio_id=2, owner_id=2, cost=990, percent=1.0)],
    )

    users = [
        create_user(
            db,
            valid_emails[0],
            valid_display_names[0],
            valid_password,
            starting_balance=1000,
        ),
        create_user(
            db,
            valid_emails[1],
            valid_display_names[1],
            valid_password,
            starting_balance=1000,
        ),
    ]
    buy_portfolio_holding(db, users[0].portfolio.id, "AAA", 90)
    invest_in_portfolio(db, users[0].portfolio.id, users[1].portfolio.id, 10)

    assert users == expected


def test_divest_from_portfolio(db, valid_emails, valid_display_names, valid_password):
    expected = [
        User(email="user0@web.com", display_name="user0", password=valid_password),
        User(email="user1@web.com", display_name="user1", password=valid_password),
    ]
    expected[0].id = 1
    expected[0].portfolio = Portfolio(
        id=1,
        holdings=[
            Holding(portfolio_id=1, symbol="AAA", cost=500.0, units=550.0),
            Holding(portfolio_id=1, symbol="USD", cost=500.0, units=550.0),
        ],
        ownership=[
            Ownership(portfolio_id=1, owner_id=1, cost=1000.0, percent=1000 / 1100),
            Ownership(portfolio_id=1, owner_id=2, cost=100.0, percent=100 / 1100),
        ],
    )
    expected[1].id = 2
    expected[1].portfolio = Portfolio(
        id=2,
        holdings=[Holding(portfolio_id=2, symbol="USD", cost=900.0, units=900.0)],
        ownership=[Ownership(portfolio_id=2, owner_id=2, cost=900.0, percent=1.0)],
    )

    users = [
        create_user(
            db,
            valid_emails[0],
            valid_display_names[0],
            valid_password,
            starting_balance=1000,
        ),
        create_user(
            db,
            valid_emails[1],
            valid_display_names[1],
            valid_password,
            starting_balance=1000,
        ),
    ]
    buy_portfolio_holding(db, users[0].portfolio.id, "AAA", 500)
    invest_in_portfolio(db, users[0].portfolio.id, users[1].portfolio.id, 400)
    divest_from_portfolio(db, users[0].portfolio.id, users[1].portfolio.id, 300)

    for i in [0, 1]:
        for user_holding, expected_holding in zip(
            users[i].portfolio.holdings, expected[i].portfolio.holdings
        ):
            assert user_holding.symbol == expected_holding.symbol
            assert user_holding.cost == approx(expected_holding.cost)
            assert user_holding.units == approx(expected_holding.units)
        for user_ownership, expected_ownership in zip(
            users[i].portfolio.ownership, expected[i].portfolio.ownership
        ):
            assert user_ownership.owner_id == expected_ownership.owner_id
            assert user_ownership.cost == approx(expected_ownership.cost)
            assert user_ownership.percent == approx(expected_ownership.percent)

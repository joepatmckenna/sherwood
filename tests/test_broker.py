from sherwood.broker import (
    buy_portfolio_holding,
    sell_portfolio_holding,
    invest_in_portfolio,
    divest_from_portfolio,
)
from sherwood.models import create_user, User, Portfolio, Holding, Ownership


def test_buy_portfolio_holding(db, valid_email, valid_display_name, valid_password):
    expected = User(
        email=valid_email, display_name=valid_display_name, password=valid_password
    )
    expected.id = 1
    expected.portfolio = Portfolio(
        cash=700,
        holdings=[
            Holding(portfolio_id=1, symbol="AAA", cost=100, units=100),
            Holding(portfolio_id=1, symbol="BBB", cost=200, units=100),
        ],
        ownership=[
            Ownership(portfolio_id=1, owner_id=1, cost=300, percent=1),
        ],
    )
    expected.portfolio.id = 1
    user = create_user(db, valid_email, valid_display_name, valid_password)
    user.portfolio.cash = 1000
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
        cash=730,
        holdings=[
            Holding(portfolio_id=1, symbol="AAA", cost=90, units=90),
            Holding(portfolio_id=1, symbol="BBB", cost=180, units=90),
        ],
        ownership=[
            Ownership(portfolio_id=1, owner_id=1, cost=270, percent=1),
        ],
    )
    expected.portfolio.id = 1

    user = create_user(db, valid_email, valid_display_name, valid_password, cash=1000)
    buy_portfolio_holding(db, user.portfolio.id, "AAA", 100)
    buy_portfolio_holding(db, user.portfolio.id, "BBB", 200)
    sell_portfolio_holding(db, user.portfolio.id, "AAA", 10)
    sell_portfolio_holding(db, user.portfolio.id, "BBB", 20)

    assert expected == db.get(User, 1)


def test_invest_in_portfolio(db, valid_emails, valid_display_names, valid_password):
    expected = [
        User(
            email="user0@web.com",
            display_name="user0",
            password=valid_password,
        ),
        User(
            email="user1@web.com",
            display_name="user1",
            password=valid_password,
        ),
    ]
    expected[0].id = 1
    expected[0].portfolio = Portfolio(
        cash=900.0,
        holdings=[
            Holding(
                portfolio_id=1,
                symbol="AAA",
                cost=100.0,
                units=200.0,
            )
        ],
        ownership=[
            Ownership(
                portfolio_id=1,
                owner_id=1,
                cost=100.0,
                percent=0.5,
            ),
            Ownership(
                portfolio_id=1,
                owner_id=2,
                cost=100.0,
                percent=0.5,
            ),
        ],
    )
    expected[0].portfolio.id = 1
    expected[1].id = 2
    expected[1].portfolio = Portfolio(
        cash=900.0,
        holdings=[],
        ownership=[],
    )
    expected[1].portfolio.id = 2

    users = [
        create_user(
            db, valid_emails[0], valid_display_names[0], valid_password, cash=1000
        ),
        create_user(
            db, valid_emails[1], valid_display_names[1], valid_password, cash=1000
        ),
    ]
    buy_portfolio_holding(db, users[0].portfolio.id, "AAA", 100)
    invest_in_portfolio(db, users[0].portfolio.id, users[1].portfolio.id, 100)

    assert users == expected


# TODO
def test_divest_from_portfolio():
    pass

from sherwood.broker import buy_portfolio_holding, sell_portfolio_holding
from sherwood.models import create_user, Holding, Ownership, Portfolio, User


def test_buy_portfolio_holding(db, valid_email, valid_password):
    expected = User(email=valid_email, password=valid_password)
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
    user = create_user(db, valid_email, valid_password)
    user.portfolio.cash = 1000
    buy_portfolio_holding(db, user.portfolio.id, "AAA", 50)
    buy_portfolio_holding(db, user.portfolio.id, "BBB", 200)
    buy_portfolio_holding(db, user.portfolio.id, "AAA", 50)
    assert expected == db.get(User, 1)


def test_sell_portfolio_holding(db, valid_email, valid_password):
    expected = User(email=valid_email, password=valid_password)
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

    user = create_user(db, valid_email, valid_password)
    user.portfolio.cash = 1000
    buy_portfolio_holding(db, user.portfolio.id, "AAA", 100)
    buy_portfolio_holding(db, user.portfolio.id, "BBB", 200)
    sell_portfolio_holding(db, user.portfolio.id, "AAA", 10)
    sell_portfolio_holding(db, user.portfolio.id, "BBB", 20)

    assert expected == db.get(User, 1)

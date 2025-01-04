import pytest
import sqlalchemy

from sherwood.models import Holding, Portfolio, User


def test_user_add_success(db, valid_password):
    user_1 = User("user_1@web.com", valid_password)
    user_2 = User("user_2@web.com", valid_password)
    db.add(user_1)
    db.add(user_2)
    db.commit()
    assert db.get(User, 1) == user_1
    assert db.get(User, 2) == user_2


def test_user_id_cannot_be_manually_assigned(valid_email, valid_password):
    with pytest.raises(TypeError):
        User(id=1, email=valid_email, password=valid_password)


def test_user_email_must_be_unique(db, valid_email, valid_password):
    db.add(User(valid_email, valid_password))
    db.add(User(valid_email, valid_password))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.commit()


def test_deleting_user_deletes_their_portfolio(db, valid_email, valid_password):
    user = User(valid_email, valid_password)
    user.portfolio = Portfolio()
    db.add(user)
    db.commit()
    assert db.get(Portfolio, 1) is not None
    db.delete(user)
    db.commit()
    assert db.get(Portfolio, 1) is None


def test_add_holdings_to_portfolio(db, valid_email, valid_password):
    user = User(valid_email, valid_password)
    user.portfolio = Portfolio()
    holding_1 = Holding(portfolio_id=user.portfolio.id, symbol="AAA", units=1, cost=100)
    holding_2 = Holding(portfolio_id=user.portfolio.id, symbol="BBB", units=2, cost=200)
    user.portfolio.holdings.extend([holding_1, holding_2])
    db.add(user.portfolio)
    db.commit()
    assert db.get(Portfolio, 1).holdings == [holding_1, holding_2]

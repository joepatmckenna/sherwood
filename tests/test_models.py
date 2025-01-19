import pytest
import sqlalchemy
import time

from sherwood.models import (
    create_quote,
    has_expired,
    update_quote,
    Holding,
    Portfolio,
    User,
)


def test_user_add_success(db, valid_emails, valid_display_name, valid_password):
    user_1 = User(valid_emails[0], valid_display_name + "1", valid_password)
    user_2 = User(valid_emails[1], valid_display_name + "2", valid_password)
    db.add(user_1)
    db.add(user_2)
    db.commit()
    assert db.get(User, 1) == user_1
    assert db.get(User, 2) == user_2


def test_user_id_cannot_be_manually_assigned(valid_email, valid_password):
    with pytest.raises(TypeError):
        User(id=1, email=valid_email, password=valid_password)


def test_user_email_must_be_unique(db, valid_email, valid_display_name, valid_password):
    db.add(User(valid_email, valid_display_name, valid_password))
    db.add(User(valid_email, valid_display_name, valid_password))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.commit()


def test_deleting_user_deletes_their_portfolio(
    db, valid_email, valid_display_name, valid_password
):
    user = User(valid_email, valid_display_name, valid_password)
    user.portfolio = Portfolio()
    db.add(user)
    db.commit()
    assert db.get(Portfolio, 1) is not None
    db.delete(user)
    db.commit()
    assert db.get(Portfolio, 1) is None


def test_add_holdings_to_portfolio(db, valid_email, valid_display_name, valid_password):
    user = User(valid_email, valid_display_name, valid_password)
    user.portfolio = Portfolio()
    holding_1 = Holding(portfolio_id=user.portfolio.id, symbol="AAA", units=1, cost=100)
    holding_2 = Holding(portfolio_id=user.portfolio.id, symbol="BBB", units=2, cost=200)
    user.portfolio.holdings.extend([holding_1, holding_2])
    db.add(user.portfolio)
    db.commit()
    assert db.get(Portfolio, 1).holdings == [holding_1, holding_2]


def test_last_updated_at_changes_on_quote_update(db):
    quote = create_quote(db, symbol="AAA", price=1)
    t = quote.last_updated_at
    time.sleep(0.1)
    update_quote(db, quote, 2)
    assert t < quote.last_updated_at


def test_has_expired(db):
    quote = create_quote(db, symbol="AAA", price=1)
    time.sleep(0.1)
    assert has_expired(quote, 0.05)
    assert not has_expired(quote, 0.2)

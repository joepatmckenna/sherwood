import pytest
from sherwood.auth import _decode_access_token
from sherwood.broker import (
    sign_up_user,
    sign_in_user,
    buy_portfolio_holding,
    sell_portfolio_holding,
    STARTING_BALANCE,
)
from sherwood.models import create_user, User, Portfolio, Holding, Ownership
from sherwood import errors


def test_sign_up_user(db, valid_email, valid_display_name, valid_password):
    expected = User(
        email=valid_email, display_name=valid_display_name, password=valid_password
    )
    expected.id = 1
    expected.portfolio = Portfolio(cash=STARTING_BALANCE)
    expected.portfolio.id = 1
    sign_up_user(db, valid_email, valid_display_name, valid_password)
    assert expected == db.get(User, 1)


def test_sign_up_user_duplicate_email(
    db, valid_email, valid_display_name, valid_password
):
    sign_up_user(db, valid_email, valid_display_name + "1", valid_password)
    with pytest.raises(errors.DuplicateUserError):
        sign_up_user(db, valid_email, valid_display_name + "1", valid_password)


def test_sign_up_user_duplicate_display_name(
    db, valid_emails, valid_display_name, valid_password
):
    sign_up_user(db, valid_emails[0], valid_display_name.lower(), valid_password)
    with pytest.raises(errors.DuplicateUserError):
        sign_up_user(db, valid_emails[1], valid_display_name.upper(), valid_password)


def test_sign_in_user(db, valid_email, valid_display_name, valid_password):
    expected = User(
        email=valid_email, display_name=valid_display_name, password=valid_password
    )
    expected.id = 1
    expected.portfolio = Portfolio()
    expected.portfolio.id = 1
    sign_up_user(db, valid_email, valid_display_name, valid_password)
    access_token = sign_in_user(db, valid_email, valid_password)
    payload = _decode_access_token(access_token)
    assert payload["sub"] == str(expected.id)


def test_sign_in_user_missing_user(db, valid_email, valid_password):
    with pytest.raises(errors.MissingUserError):
        sign_in_user(db, valid_email, valid_password)


def test_sign_in_user_incorrect_password(
    db, valid_email, valid_display_name, valid_password
):
    sign_up_user(db, valid_email, valid_display_name, valid_password)
    with pytest.raises(errors.IncorrectPasswordError):
        sign_in_user(db, valid_email, "password")


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

    user = create_user(db, valid_email, valid_display_name, valid_password)
    user.portfolio.cash = 1000
    buy_portfolio_holding(db, user.portfolio.id, "AAA", 100)
    buy_portfolio_holding(db, user.portfolio.id, "BBB", 200)
    sell_portfolio_holding(db, user.portfolio.id, "AAA", 10)
    sell_portfolio_holding(db, user.portfolio.id, "BBB", 20)

    assert expected == db.get(User, 1)


# TODO
def test_invest_in_portfolio():
    pass


# TODO
def test_divest_from_portfolio():
    pass

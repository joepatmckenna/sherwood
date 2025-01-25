import pytest
from sherwood.auth import _decode_access_token
from sherwood.errors import DuplicateUserError, IncorrectPasswordError, MissingUserError
from sherwood.models import User
from sherwood.registrar import sign_up_user, sign_in_user, STARTING_BALANCE


def test_sign_up_user_success(db, valid_email, valid_display_name, valid_password):
    expected = sign_up_user(db, valid_email, valid_display_name, valid_password)
    user = db.get(User, 1)
    assert user == expected
    holding = user.portfolio.holdings[0]
    assert holding.symbol == "USD"
    assert holding.units == holding.cost == STARTING_BALANCE


def test_sign_up_user_duplicate_email(
    db, valid_email, valid_display_names, valid_password
):
    sign_up_user(db, valid_email, valid_display_names[0], valid_password)
    with pytest.raises(DuplicateUserError):
        sign_up_user(db, valid_email, valid_display_names[1], valid_password)


def test_sign_up_user_duplicate_display_name(
    db, valid_emails, valid_display_name, valid_password
):
    sign_up_user(db, valid_emails[0], valid_display_name.upper(), valid_password)
    with pytest.raises(DuplicateUserError):
        sign_up_user(db, valid_emails[1], valid_display_name.lower(), valid_password)


def test_sign_in_user_success(db, valid_email, valid_display_name, valid_password):
    user = sign_up_user(db, valid_email, valid_display_name, valid_password)
    access_token = sign_in_user(db, valid_email, valid_password)
    payload = _decode_access_token(access_token)
    assert payload["sub"] == str(user.id)


def test_sign_in_user_missing_user(db, valid_email, valid_display_name, valid_password):
    with pytest.raises(MissingUserError):
        sign_in_user(db, valid_email, valid_password)


def test_sign_in_user_incorrect_password(
    db, valid_email, valid_display_name, valid_password
):
    sign_up_user(db, valid_email, valid_display_name, valid_password)
    with pytest.raises(IncorrectPasswordError):
        sign_in_user(db, valid_email, "wrong password")

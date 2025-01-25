from sherwood.auth import (
    generate_access_token,
    password_context,
    ACCESS_TOKEN_LIFESPAN_HOURS,
)
from sherwood.db import maybe_commit
from sherwood.errors import DuplicateUserError, IncorrectPasswordError, MissingUserError
from sherwood.models import create_user, User
from sqlalchemy import func
from sqlalchemy.exc import MultipleResultsFound

STARTING_BALANCE = 10_000


def sign_up_user(db, email, display_name, password):
    if db.query(User).filter_by(email=email).first() is not None:
        raise DuplicateUserError(email=email)
    if (
        db.query(User)
        .filter(func.lower(User.display_name) == display_name.lower())
        .first()
        is not None
    ):
        raise DuplicateUserError(display_name=display_name)
    return create_user(
        db=db,
        email=email,
        display_name=display_name,
        password=password,
        starting_balance=STARTING_BALANCE,
    )


def sign_in_user(db, email, password):
    try:
        user = db.query(User).filter_by(email=email).one_or_none()
    except MultipleResultsFound:
        raise DuplicateUserError(email=email)
    if user is None:
        raise MissingUserError(email=email)
    if not password_context.verify(password, user.password):
        raise IncorrectPasswordError()
    if password_context.needs_update(user.password):
        user.password = password_context.hash(user.password)
        maybe_commit(db, "Failed to update password hash.")
    return generate_access_token(user, ACCESS_TOKEN_LIFESPAN_HOURS)

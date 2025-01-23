from calendar import timegm
import datetime
from enum import Enum
from fastapi import Cookie, Depends
import jose.jwt
import os
from passlib.context import CryptContext
import re
from sherwood.db import Database
from sherwood.errors import (
    InternalServerError,
    InvalidAccessTokenError,
    InvalidDisplayNameError,
    InvalidPasswordError,
    MissingUserError,
)
from sherwood.models import User
from sqlalchemy.event import listens_for
from typing import Annotated
from uuid import uuid4


AUTHORIZATION_COOKIE_NAME = "x_sherwood_authorization"

JWT_SECRET_KEY_ENV_VAR_NAME = "JWT_SECRET_KEY"

_JWT_ISSUER = "sherwood"
_JWT_ALGORITHM = "HS256"
_JWT_DURATION_HOURS = 4

_MIN_DISPLAY_NAME_LENGTH = 3
_MAX_DISPLAY_NAME_LENGTH = 32

_MIN_PASSWORD_LENGTH = 8
_MAX_PASSWORD_LENGTH = 32

password_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def _validate_env() -> None:
    if os.environ.get(JWT_SECRET_KEY_ENV_VAR_NAME) is None:
        raise InternalServerError(
            f"Missing environment variable {JWT_SECRET_KEY_ENV_VAR_NAME}"
        )


class ReasonDisplayNameInvalid(Enum):
    TOO_SHORT = (
        f"Display name must be at least {_MIN_DISPLAY_NAME_LENGTH} characters long."
    )
    TOO_Long = (
        f"Display name must not be longer than {_MAX_DISPLAY_NAME_LENGTH} characters."
    )
    CONTAINS_SPECIAL = "Display name must only use letters (a-z or A-Z), numbers (0-9), underscores (_), hyphens (-), or periods (.)."
    STARTS_WITH_SPECIAL = "Display name must begin with a letter (a-z or A-Z)."


def validate_display_name(display_name: str) -> list[str]:
    reasons = []
    if len(display_name) < _MIN_DISPLAY_NAME_LENGTH:
        reasons.append(ReasonDisplayNameInvalid.TOO_SHORT.value)
    if len(display_name) > _MAX_DISPLAY_NAME_LENGTH:
        reasons.append(ReasonDisplayNameInvalid.TOO_LONG.value)
    if not re.match(r"^[a-zA-Z0-9._\-]+$", display_name):
        reasons.append(ReasonDisplayNameInvalid.CONTAINS_SPECIAL.value)
    if not re.match(r"^[a-zA-Z]", display_name):
        reasons.append(ReasonDisplayNameInvalid.STARTS_WITH_SPECIAL.value)
    return reasons


class ReasonPasswordInvalid(Enum):
    TOO_SHORT = f"Password must be at least {_MIN_PASSWORD_LENGTH} characters long."
    TOO_LONG = f"Password must not be longer than {_MAX_PASSWORD_LENGTH} characters."
    CONTAINS_SPACE = "Password must not contain spaces."
    MISSING_LOWERCASE = "Password must contain at least one lowercase letter."
    MISSING_UPPERCASE = "Password must contain at least one uppercase letter."
    MISSING_DIGIT = "Password must contain at least one digit."
    MISSING_SPECIAL = "Password must contain at least one special character."


def validate_password(password: str) -> list[str]:
    reasons = list()
    if len(password) < _MIN_PASSWORD_LENGTH:
        reasons.append(ReasonPasswordInvalid.TOO_SHORT.value)
    if len(password) > _MAX_PASSWORD_LENGTH:
        reasons.append(ReasonPasswordInvalid.TOO_LONG.value)
    if re.search(r"\s", password):
        reasons.append(ReasonPasswordInvalid.CONTAINS_SPACE.value)
    if not re.search(r"[a-z]", password):
        reasons.append(ReasonPasswordInvalid.MISSING_LOWERCASE.value)
    if not re.search(r"[A-Z]", password):
        reasons.append(ReasonPasswordInvalid.MISSING_UPPERCASE.value)
    if not re.search(r"[0-9]", password):
        reasons.append(ReasonPasswordInvalid.MISSING_DIGIT.value)
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        reasons.append(ReasonPasswordInvalid.MISSING_SPECIAL.value)
    return reasons


@listens_for(User, "before_insert")
def validate_user(mapper, connection, target):
    if reasons := validate_display_name(target.display_name):
        raise InvalidDisplayNameError(reasons)
    if reasons := validate_password(target.password):
        raise InvalidPasswordError(reasons)
    target.password = password_context.hash(target.password)


def generate_access_token(user, hours: float = _JWT_DURATION_HOURS) -> str:
    _validate_env()
    issued_at = datetime.datetime.now(datetime.timezone.utc)
    expiration = issued_at + datetime.timedelta(hours=hours)
    try:
        return jose.jwt.encode(
            claims={
                "iss": _JWT_ISSUER,
                "sub": str(user.id),
                "exp": timegm(expiration.utctimetuple()),
                "iat": timegm(issued_at.utctimetuple()),
                "jti": str(uuid4()),
            },
            key=os.environ[JWT_SECRET_KEY_ENV_VAR_NAME],
            algorithm=_JWT_ALGORITHM,
        )
    except jose.jwt.JWTError as exc:
        raise InternalServerError(
            f"Failed to generate access token. Error: {exc}"
        ) from exc


def _decode_access_token(access_token: str) -> dict[str, str]:
    _validate_env()
    try:
        return jose.jwt.decode(
            access_token,
            key=os.environ[JWT_SECRET_KEY_ENV_VAR_NAME],
            algorithms=[_JWT_ALGORITHM],
            issuer=_JWT_ISSUER,
        )
    except (
        jose.jwt.ExpiredSignatureError,
        jose.jwt.JWTClaimsError,
        jose.jwt.JWTError,
    ) as exc:
        raise InvalidAccessTokenError(
            f"Failed to decode access_token. Error: {exc}."
        ) from exc


async def authorized_user(
    db: Database, x_sherwood_authorization: Annotated[str | None, Cookie()] = None
):
    if x_sherwood_authorization is None:
        raise InvalidAccessTokenError(detail="Missing X-Sherwood-Authorization.")

    token_type, _, access_token = x_sherwood_authorization.partition(" ")
    if token_type.strip().lower() != "bearer":
        raise InvalidAccessTokenError(detail=f"Token type '{token_type}' != 'Bearer'")

    payload = _decode_access_token(access_token)

    user_id = payload["sub"]
    if (user := db.get(User, user_id)) is None:
        raise MissingUserError(user_id=user_id)

    return user


AuthorizedUser = Annotated[User, Depends(authorized_user)]


def get_cookie_security() -> bool:
    return True


CookieSecurity = Annotated[bool, Depends(get_cookie_security)]

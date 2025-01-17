from calendar import timegm
import datetime
from enum import Enum
from fastapi import Cookie, Depends
import jose.jwt
import logging
import os
from passlib.context import CryptContext
import re
from sherwood import errors
from sherwood.auth import decode_access_token
from sherwood.db import Database
from sherwood.models import User
from typing import Annotated
from uuid import uuid4

AUTHORIZATION_COOKIE_NAME = "x_sherwood_authorization"

JWT_SECRET_KEY_ENV_VAR_NAME = "JWT_SECRET_KEY"

_JWT_ISSUER = "sherwood"
_JWT_ALGORITHM = "HS256"
_JWT_DURATION_HOURS = 4

_MIN_PASSWORD_LENGTH = 8
_MAX_PASSWORD_LENGTH = 32

password_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


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


def _validate_env() -> None:
    if os.environ.get(JWT_SECRET_KEY_ENV_VAR_NAME) is None:
        raise errors.InternalServerError(
            f"Missing environment variable {JWT_SECRET_KEY_ENV_VAR_NAME}"
        )


def generate_access_token(user: User, hours: float = _JWT_DURATION_HOURS) -> str:
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
        raise errors.InternalServerError(f"Failed to generate access token. Error: {exc}") from exc
    except Exception as exc:
        raise errors.InternalServerError(f"Failed to generate access token. Unexpected Error: {exc}") from exc


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
        raise errors.InvalidAccessToken(f"Failed to decode access_token. Error: {exc}.)
    except Exception as exc:
        raise errors.InternalServerError(f"Failed to decode access_token. Unexpected Error: {exc}.)


async def _authorized_user(
    db: Database, x_sherwood_authorization: Annotated[str | None, Cookie()] = None
) -> User:
    if x_sherwood_authorization is None:
        raise errors.InvalidAccessToken(detail="Missing X-Sherwood-Authorization.")

    token_type, _, access_token = x_sherwood_authorization.partition(" ")
    if token_type.strip().lower() != "bearer":
        raise errors.InvalidAccessToken(detail=f"Token type '{token_type}' != 'Bearer'")

    payload = _decode_access_token(access_token)

    user_id = payload["sub"]
    if (user := db.get(User, user_id)) is None:
        raise errors.MissingUserError(user_id=user_id)

    return user


AuthorizedUser = Annotated[User, Depends(_authorized_user)]


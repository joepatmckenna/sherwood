from calendar import timegm
import datetime
from enum import Enum
import jose.jwt
import logging
import os
from passlib.context import CryptContext
import re
from uuid import uuid4

JWT_SECRET_KEY_ENV_VAR_NAME = "JWT_SECRET_KEY"
_JWT_ISSUER = "sherwood"
_JWT_ALGORITHM = "HS256"
_JWT_DURATION_HOURS = 4

password_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

_MIN_PASSWORD_LENGTH = 8
_MAX_PASSWORD_LENGTH = 32


class ReasonPasswordInvalid(Enum):
    TOO_SHORT = f"Password must be at least {_MIN_PASSWORD_LENGTH} characters long."
    TOO_LONG = f"Password must not be longer than {_MAX_PASSWORD_LENGTH} characters."
    CONTAINS_SPACE = "Password must not contain spaces."
    MISSING_LOWERCASE = "Password must contain at least one lowercase letter."
    MISSING_UPPERCASE = "Password must contain at least one uppercase letter."
    MISSING_DIGIT = "Password must contain at least one digit."
    MISSING_SPECIAL = "Password must contain at least one special character."


def validate_password(password: str) -> tuple[bool, list[str]]:
    is_valid = True
    reasons = list()
    if len(password) < _MIN_PASSWORD_LENGTH:
        is_valid = False
        reasons.append(ReasonPasswordInvalid.TOO_SHORT.value)
    if len(password) > _MAX_PASSWORD_LENGTH:
        is_valid = False
        reasons.append(ReasonPasswordInvalid.TOO_LONG.value)
    if re.search(r"\s", password):
        is_valid = False
        reasons.append(ReasonPasswordInvalid.CONTAINS_SPACE.value)
    if not re.search(r"[a-z]", password):
        is_valid = False
        reasons.append(ReasonPasswordInvalid.MISSING_LOWERCASE.value)
    if not re.search(r"[A-Z]", password):
        is_valid = False
        reasons.append(ReasonPasswordInvalid.MISSING_UPPERCASE.value)
    if not re.search(r"[0-9]", password):
        is_valid = False
        reasons.append(ReasonPasswordInvalid.MISSING_DIGIT.value)
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        is_valid = False
        reasons.append(ReasonPasswordInvalid.MISSING_SPECIAL.value)
    return is_valid, reasons


def _validate_env():
    if os.environ.get(JWT_SECRET_KEY_ENV_VAR_NAME) is None:
        raise RuntimeError(
            f"Missing environment variable {JWT_SECRET_KEY_ENV_VAR_NAME}"
        )


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
        logging.error(f"General token error: {exc}")
        raise


def decode_access_token(access_token: str) -> dict[str, str]:
    _validate_env()
    try:
        return jose.jwt.decode(
            access_token,
            key=os.environ[JWT_SECRET_KEY_ENV_VAR_NAME],
            algorithms=[_JWT_ALGORITHM],
            issuer=_JWT_ISSUER,
        )
    except jose.jwt.ExpiredSignatureError:
        logging.error("Token has expired.")
        raise
    except jose.jwt.JWTClaimsError as exc:
        logging.error(f"Invalid claims: {exc}")
        raise
    except jose.jwt.JWTError as exc:
        logging.error(f"General token error: {exc}")
        raise

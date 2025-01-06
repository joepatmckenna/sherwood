from calendar import timegm
import datetime
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


def _validate_env():
    if os.environ.get(JWT_SECRET_KEY_ENV_VAR_NAME) is None:
        raise RuntimeError(
            f"Missing environment variable {JWT_SECRET_KEY_ENV_VAR_NAME}"
        )


def validate_password(
    password: str, min_length: int = 8, max_length: int = 32
) -> tuple[bool, list[str]]:
    is_valid = True
    reasons = list()
    if len(password) < min_length:
        is_valid = False
        reasons.append(f"Password must be at least {min_length} characters long.")
    if len(password) > max_length:
        is_valid = False
        reasons.append(f"Password must not be longer than {max_length} characters.")
    if not re.search(r"[a-z]", password):
        is_valid = False
        reasons.append("Password must contain at least one lowercase letter.")
    if not re.search(r"[A-Z]", password):
        is_valid = False
        reasons.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[0-9]", password):
        is_valid = False
        reasons.append("Password must contain at least one digit.")
    if re.search(r"\s", password):
        is_valid = False
        reasons.append("Password must not contain spaces.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        is_valid = False
        reasons.append("Password must contain at least one special character.")
    return is_valid, reasons


def generate_jwt_for_user(user, hours: float = _JWT_DURATION_HOURS) -> str:
    _validate_env()
    issued_at = datetime.datetime.now(datetime.timezone.utc)
    expiration = issued_at + datetime.timedelta(hours=hours)
    try:
        return jose.jwt.encode(
            claims={
                "iss": _JWT_ISSUER,
                "sub": str(user.id),
                "aud": user.email,
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


def decode_jwt_for_user(jwt: str, email: str) -> dict[str, str]:
    _validate_env()
    try:
        return jose.jwt.decode(
            jwt,
            key=os.environ[JWT_SECRET_KEY_ENV_VAR_NAME],
            algorithms=[_JWT_ALGORITHM],
            audience=email,
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

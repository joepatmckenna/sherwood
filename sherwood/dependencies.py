from fastapi import Cookie, Depends
import logging
from sherwood import errors
from sherwood.auth import decode_access_token
from sherwood.db import get_db
from sherwood.models import User
from sqlalchemy.orm import Session as SqlAlchemyOrmSession
from typing import Annotated


Database = Annotated[SqlAlchemyOrmSession, Depends(get_db)]


AUTHORIZATION_COOKIE_NAME = "x_sherwood_authorization"


async def authorized_user(
    db: Database, x_sherwood_authorization: Annotated[str | None, Cookie()] = None
) -> User:
    if x_sherwood_authorization is None:
        raise errors.InvalidAccessToken(detail="Missing X-Sherwood-Authorization.")

    token_type, _, access_token = x_sherwood_authorization.partition(" ")
    if token_type.strip().lower() != "bearer":
        raise errors.InvalidAccessToken(detail=f"Token type '{token_type}' != 'Bearer'")

    try:
        payload = decode_access_token(access_token)
    except Exception as exc:
        raise errors.InvalidAccessToken(
            detail=f"Failed to decode access token, error: {exc}"
        ) from exc

    user_id = payload["sub"]
    user = db.get(User, user_id)
    if user is None:
        logging.error(f"Access token for missing user, ID: {user_id}")
        raise errors.MissingUserError(user_id=user_id)

    return user


AuthorizedUser = Annotated[User, Depends(authorized_user)]

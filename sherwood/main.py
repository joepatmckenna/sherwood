from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import status, Depends, FastAPI, Header
import gunicorn.app.base
import logging
import os
from pydantic import BaseModel, EmailStr
from sherwood import errors
from sherwood.auth import (
    decode_access_token,
    generate_access_token,
    password_context,
    validate_password,
)
from sherwood.db import get_db, Session, POSTGRESQL_DATABASE_URL_ENV_VAR_NAME
from sherwood.models import create_user, to_dict, BaseModel as Base, User
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SqlAlchemyOrmSession
from typing import Annotated

logging.basicConfig(level=logging.DEBUG)

Database = Annotated[SqlAlchemyOrmSession, Depends(get_db)]


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str


class SignUpResponse(BaseModel):
    pass


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class SignInResponse(BaseModel):
    token_type: str
    access_token: str


async def authorized_user(
    db: Database, x_sherwood_authorization: Annotated[str | None, Header()] = None
) -> dict | None:
    token_type, _, access_token = x_sherwood_authorization.partition(" ")
    if token_type.strip().lower() != "bearer":
        logging.error(
            f"Authorization with token type other than bearer detected, token type: {token_type}."
        )
        return

    try:
        payload = decode_access_token(access_token)
    except Exception as exc:
        logging.error(f"Failed to decode access token: {exc}")
        return

    user = db.get(User, payload["sub"])
    if user is None:
        logging.error(
            f"Decoded access token contains ID {payload['sub']} that doesn't match a user"
        )

    return {**to_dict(user), **{"access_token": access_token}}


MaybeAuthorizedUser = Annotated[dict | None, Depends(authorized_user)]


def create_app(*args, **kwargs):
    app = FastAPI(*args, **kwargs)

    @app.get("/")
    async def root():
        return {}

    @app.post("/sign_up")
    async def sign_up(request: SignUpRequest, db: Database) -> SignUpResponse:
        logging.info(f"Got sign up request: {request}")

        user = db.query(User).filter_by(email=request.email).first()
        if user is not None:
            logging.error(f"Email {request.email} already signed up.")
            raise errors.DuplicateUserError(status.HTTP_409_CONFLICT, request.email)

        is_valid, reasons = validate_password(request.password)
        if not is_valid:
            logging.error(
                f"Requested password {request.password} invalid because: {reasons}"
            )
            raise errors.InvalidPasswordError(status.HTTP_400_BAD_REQUEST, reasons)

        try:
            user = create_user(db, request.email, request.password)
        except Exception as exc:
            logging.error(f"Error creating user, request={request}, error={exc}")
            raise errors.InternalServerError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error. Failed to create user.",
            )

        return {}

    @app.post("/sign_in")
    async def sign_in(request: SignInRequest, db: Database) -> SignInResponse:
        user = db.query(User).filter_by(email=request.email).first()
        if user is None:
            raise errors.MissingUserError(status.HTTP_404_NOT_FOUND, request.email)

        if not password_context.verify(request.password, user.password):
            raise errors.IncorrectPasswordError(status.HTTP_401_UNAUTHORIZED)

        if password_context.needs_update(user.password):
            user.password = password_context.hash(request.password)
            try:
                db.commit()
            except Exception as exc:
                db.rollback()
                logging.error(
                    f"Failed to updated password for user: {user}, error: {exc}."
                )

        try:
            access_token = generate_access_token(user)
        except Exception as exc:
            logging.error(
                f"Failed to generate access token for user: {user}, error: {exc}"
            )
            raise errors.InternalServerError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error. Failed to generate access token.",
            )

        return SignInResponse(token_type="Bearer", access_token=access_token)

    @app.get("/user")
    async def get_authorized_user(user: MaybeAuthorizedUser = None):
        return user or {}

    for error in errors.errors:
        app.add_exception_handler(error, errors.error_handler)
    return app


class App(gunicorn.app.base.BaseApplication):
    def load_config(self):
        opts = vars(self.cfg.parser().parse_args())
        for key, val in opts.items():
            if val is None:
                continue
            key = key.lower()
            if key in {"args", "worker_class"}:
                continue
            self.cfg.set(key, val)
        self.cfg.set(
            "worker_class",
            "uvicorn.workers.UvicornWorker",
        )
        if not opts.get("workers"):
            self.cfg.set("workers", 2 * os.cpu_count() + 1)

    def load(self):
        load_dotenv(".env")

        postgresql_database_url = os.environ.get(POSTGRESQL_DATABASE_URL_ENV_VAR_NAME)
        if not postgresql_database_url:
            raise RuntimeError(
                f"Environment variable '{POSTGRESQL_DATABASE_URL_ENV_VAR_NAME}' is not set."
            )

        engine = create_engine(postgresql_database_url)
        Session.configure(bind=engine)

        @asynccontextmanager
        async def lifespan(_):
            Base.metadata.create_all(engine)
            yield
            engine().dispose()

        return create_app(title="sherwood", version="0.0.0", lifespan=lifespan)


if __name__ == "__main__":
    App().run()

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import status, Depends, FastAPI, Header
import gunicorn.app.base
import logging
import os
from pydantic import BaseModel, EmailStr
from sherwood import errors
from sherwood.auth import (
    decode_jwt_for_user,
    generate_jwt_for_user,
    password_context,
    validate_password,
)
from sherwood.db import (
    get_db,
    Session,
    POSTGRESQL_DATABASE_URL_ENV_VAR_NAME,
)
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
    jwt: str | None = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class SignInResponse(BaseModel):
    jwt: str


async def authorized_user(
    db: Database,
    user: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict | None:
    try:
        token_type, _, jwt = authorization.partition(" ")
        assert token_type.strip().upper() == "BEARER"
        decode_jwt_for_user(jwt, user)
        user = db.query(User).filter_by(email=user).first()
        assert user is not None
        user_dict = to_dict(user)
        user_dict["jwt"] = jwt
        return user_dict
    except:
        pass


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
                message="Internal server error.",
            )
        response = SignUpResponse()
        try:
            response.jwt = generate_jwt_for_user(user)
        except Exception as exc:
            logging.error(f"Error generating JWT for user {user}, error={exc}")
        return response

    @app.post("/sign_in")
    async def sign_in(
        request: SignInRequest,
        db: Database,
        # user_info: Annotated[dict | None, Depends(authorized_user)] = None,
    ) -> SignInResponse:
        # if user_info is not None and ((jwt := user_info.get("jwt")) is not None):
        #     return SignInResponse(jwt=jwt)
        user = db.query(User).filter_by(email=request.email).first()
        if user is None:
            raise errors.MissingUserError(status.HTTP_404_NOT_FOUND, request.email)
        if not password_context.verify(request.password, user.password):
            raise errors.IncorrectPasswordError(status.HTTP_401_UNAUTHORIZED)
        if password_context.needs_update(user.password):
            user.password = password_context.hash(request.password)
            db.commit()
        return SignInResponse(jwt=generate_jwt_for_user(user))

    @app.get("/user")
    async def get_authorized_user(
        user: Annotated[dict | None, Depends(authorized_user)] = None,
    ):
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
            self.cfg.set("workers", os.cpu_count())

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

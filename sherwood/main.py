from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header
import gunicorn.app.base
import logging
import os
from pydantic import field_validator, BaseModel, EmailStr
from sherwood import errors
from sherwood.auth import decode_access_token, validate_password
from sherwood.broker import buy_portfolio_holding, sign_in_user, sign_up_user
from sherwood.db import get_db, Session, POSTGRESQL_DATABASE_URL_ENV_VAR_NAME
from sherwood.models import to_dict, BaseModel as Base, User
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SqlAlchemyOrmSession
from typing import Annotated

logging.basicConfig(level=logging.DEBUG)


# reuable request validators


class _ModelWithEmail(BaseModel):
    email: EmailStr


class EmailValidatorMixin:
    @field_validator("email")
    def validate_email(cls, email):
        try:
            _ModelWithEmail(email=email)
            return email
        except ValueError as exc:
            raise errors.RequestValueError(
                f"Invalid email: {email}. Error: {exc.errors()[0]['msg']}",
            ) from exc


class PasswordValidatorMixin:
    @field_validator("password")
    def validate_password_format(cls, password):
        is_valid, reasons = validate_password(password)
        if not is_valid:
            raise errors.InvalidPasswordError(reasons)
        return password


class DollarsArePositiveValidatorMixin:
    @field_validator("dollars")
    def validate_dollars_are_positive(cls, dollars):
        if dollars <= 0:
            raise errors.RequestValueError("Dollars must be positive.")
        return dollars


# requests


class SignUpRequest(BaseModel, EmailValidatorMixin, PasswordValidatorMixin):
    email: str
    password: str


class SignInRequest(BaseModel, EmailValidatorMixin):
    email: str
    password: str


class BuyRequest(BaseModel, DollarsArePositiveValidatorMixin):
    symbol: str
    dollars: float


class SellRequest(BaseModel, DollarsArePositiveValidatorMixin):
    symbol: str
    dollars: float


# responses


class SignUpResponse(BaseModel):
    pass


class SignInResponse(BaseModel):
    token_type: str
    access_token: str


class BuyResponse(BaseModel):
    pass


class SellResponse(BaseModel):
    pass


# route dependencies

Database = Annotated[SqlAlchemyOrmSession, Depends(get_db)]


async def authorized_user(
    db: Database, x_sherwood_authorization: Annotated[str | None, Header()] = None
) -> User:
    if x_sherwood_authorization is None:
        raise errors.InvalidAccessToken(
            detail="Missing X-Sherwood-Authorization header."
        )

    token_type, _, access_token = x_sherwood_authorization.partition(" ")
    if token_type.strip().lower() != "bearer":
        raise errors.InvalidAccessToken(detail=f"Token type '{token_type}' != 'Bearer'")

    try:
        payload = decode_access_token(access_token)
    except Exception as exc:
        logging.error(f"Failed to decode access token, error: {exc}")
        raise errors.InvalidAccessToken(detail="Failed to decode access token") from exc

    user_id = payload["sub"]
    user = db.get(User, user_id)
    if user is None:
        logging.error(f"Access token for missing user, ID: {user_id}")
        raise errors.MissingUserError(user_id=user_id)

    return user


AuthorizedUser = Annotated[User, Depends(authorized_user)]

# app


def create_app(*args, **kwargs):
    app = FastAPI(*args, **kwargs)

    @app.get("/")
    async def get_root():
        return {}

    @app.get("/user")
    async def get_user(user: AuthorizedUser):
        try:
            return to_dict(user)
        except (
            errors.InvalidAccessToken,
            errors.MissingUserError,
        ):
            raise
        except Exception as exc:
            msg = "Failed to detect user from X-Sherwood-Authorization header."
            logging.error(f"{msg}. Error: {exc}.")
            raise errors.InternalServerError(msg)

    @app.post("/sign-up")
    async def post_sign_up(request: SignUpRequest, db: Database) -> SignUpResponse:
        try:
            sign_up_user(db, request.email, request.password)
            return SignUpResponse()
        except (
            errors.DuplicateUserError,
            errors.InternalServerError,
        ):
            raise
        except Exception as exc:
            msg = "Failed to sign up user."
            logging.error(f"{msg} Request: {request}. Error: {exc}.")
            raise errors.InternalServerError(msg)

    @app.post("/sign-in")
    async def post_sign_in(request: SignInRequest, db: Database) -> SignInResponse:
        try:
            access_token = sign_in_user(db, request.email, request.password)
            return SignInResponse(token_type="Bearer", access_token=access_token)
        except (
            errors.DuplicateUserError,
            errors.IncorrectPasswordError,
            errors.InternalServerError,
            errors.MissingUserError,
        ):
            raise
        except Exception as exc:
            msg = "Failed to sign in user."
            logging.error(f"{msg} Request: {request}. Error: {exc}.")
            raise errors.InternalServerError(msg)

    @app.post("/buy")
    async def post_buy(
        request: BuyRequest, db: Database, user: AuthorizedUser
    ) -> BuyResponse:
        try:
            buy_portfolio_holding(
                db, user.portfolio.id, request.symbol, request.dollars
            )
            return BuyResponse()
        except (
            errors.DuplicatePortfolioError,
            errors.InsufficientCashError,
            errors.MissingPortfolioError,
        ):
            raise
        except Exception as exc:
            msg = "Failed to buy holding."
            logging.error(f"{msg} Request: {request}. Error: {exc}.")
            raise errors.InternalServerError(msg) from exc

    for error in errors.SherwoodError.__subclasses__():
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
            engine.dispose()

        return create_app(title="sherwood", version="0.0.0", lifespan=lifespan)


if __name__ == "__main__":
    App().run()

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header
import gunicorn.app.base
import logging
import os
from sherwood import errors
from sherwood.auth import decode_access_token
from sherwood.broker import (
    sign_up_user,
    sign_in_user,
    deposit_cash_into_portfolio,
    withdraw_cash_from_portfolio,
    buy_portfolio_holding,
    sell_portfolio_holding,
    invest_in_portfolio,
    divest_from_portfolio,
)
from sherwood.db import get_db, Session, POSTGRESQL_DATABASE_URL_ENV_VAR_NAME
from sherwood.errors import error_handler
from sherwood.models import to_dict, BaseModel as Base, User
from sherwood.sherwood_requests import (
    SignUpRequest,
    SignInRequest,
    DepositRequest,
    WithdrawRequest,
    BuyRequest,
    SellRequest,
    InvestRequest,
    DivestRequest,
)
from sherwood.sherwood_responses import (
    SignUpResponse,
    SignInResponse,
    DepositResponse,
    WithdrawResponse,
    BuyResponse,
    SellResponse,
    InvestResponse,
    DivestResponse,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SqlAlchemyOrmSession
from typing import Annotated

logging.basicConfig(level=logging.DEBUG)


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


router = APIRouter(prefix="")


@router.post("/sign-up")
async def post_sign_up(request: SignUpRequest, db: Database) -> SignUpResponse:
    try:
        sign_up_user(db, request.email, request.password)
        return SignUpResponse(redirect_url="/sign-in.html")
    except (
        errors.DuplicateUserError,
        errors.InternalServerError,
    ):
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to sign up user. Request: {request}. Error: {exc}."
        )


@router.post("/sign-in")
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
        raise errors.InternalServerError(
            f"Failed to sign in user. Request: {request}. Error: {exc}."
        )


@router.get("/user")
async def get_user(user: AuthorizedUser):
    try:
        return to_dict(user)
    except (
        errors.InvalidAccessToken,
        errors.MissingUserError,
    ):
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to detect user from X-Sherwood-Authorization header. Error: {exc}."
        )


@router.post("/deposit")
async def post_deposit(
    request: DepositRequest, db: Database, user: AuthorizedUser
) -> BuyResponse:
    try:
        starting_balance = user.portfolio.cash
        deposit_cash_into_portfolio(db, user.portfolio.id, request.dollars)
        ending_balance = user.portfolio.cash
        return DepositResponse(
            starting_balance=starting_balance,
            ending_balance=ending_balance,
        )
    except (
        errors.DuplicatePortfolioError,
        errors.MissingPortfolioError,
        errors.InternalServerError,
    ):
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to deposit cash. Request: {request}. Error: {exc}."
        ) from exc


@router.post("/withdraw")
async def post_withdraw(
    request: WithdrawRequest, db: Database, user: AuthorizedUser
) -> BuyResponse:
    try:
        starting_balance = user.portfolio.cash
        withdraw_cash_from_portfolio(db, user.portfolio.id, request.dollars)
        ending_balance = user.portfolio.cash
        return WithdrawResponse(
            starting_balance=starting_balance,
            ending_balance=ending_balance,
        )
    except (
        errors.DuplicatePortfolioError,
        errors.InsufficientCashError,
        errors.MissingPortfolioError,
        errors.InternalServerError,
    ):
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to deposit cash. Request: {request}. Error: {exc}."
        ) from exc


@router.post("/buy")
async def post_buy(
    request: BuyRequest, db: Database, user: AuthorizedUser
) -> BuyResponse:
    try:
        buy_portfolio_holding(db, user.portfolio.id, request.symbol, request.dollars)
        return BuyResponse()
    except (
        errors.DuplicatePortfolioError,
        errors.InsufficientCashError,
        errors.MissingPortfolioError,
        errors.InternalServerError,
    ):
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to buy holding. Request: {request}. Error: {exc}."
        ) from exc


@router.post("/sell")
async def post_sell(
    request: SellRequest, db: Database, user: AuthorizedUser
) -> BuyResponse:
    try:
        sell_portfolio_holding(db, user.portfolio.id, request.symbol, request.dollars)
        return SellResponse()
    except (
        errors.DuplicatePortfolioError,
        errors.InsufficientHoldingsError,
        errors.MissingPortfolioError,
        errors.InternalServerError,
    ):
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to sell holding. Request: {request}. Error: {exc}."
        ) from exc


@router.post("/invest")
async def post_invest(
    request: InvestRequest, db: Database, user: AuthorizedUser
) -> InvestResponse:
    try:
        invest_in_portfolio(
            db,
            request.investee_portfolio_id,
            user.portfolio.id,
            request.dollars,
        )
        return InvestResponse()
    except (
        errors.InternalServerError,
        errors.RequestValueError,
        errors.InsufficientCashError,
        errors.InsufficientHoldingsError,
    ):
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to invest in portfolio. Request: {request}. Error: {exc}."
        ) from exc


@router.post("/divest")
async def post_divest(
    request: DivestRequest, db: Database, user: AuthorizedUser
) -> DivestResponse:
    try:
        divest_from_portfolio(
            db,
            request.investee_portfolio_id,
            user.portfolio.id,
            request.dollars,
        )
        return DivestResponse()
    except (
        errors.InternalServerError,
        errors.RequestValueError,
        errors.InsufficientHoldingsError,
    ):
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to divest from portfolio. Request: {request}. Error: {exc}."
        ) from exc


def create_app(*args, **kwargs):
    app = FastAPI(*args, **kwargs)
    app.include_router(router)
    for error in errors.SherwoodError.__subclasses__():
        app.add_exception_handler(error, error_handler)
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

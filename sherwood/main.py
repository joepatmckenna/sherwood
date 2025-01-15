from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    Header,
    WebSocket,
    WebSocketDisconnect,
)
import gunicorn.app.base
import logging
import os
from sherwood import errors
from sherwood.auth import decode_access_token, validate_password
from sherwood.broker import (
    sign_up_user,
    sign_in_user,
    buy_portfolio_holding,
    sell_portfolio_holding,
    invest_in_portfolio,
    divest_from_portfolio,
)
from sherwood.db import get_db, Session, POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME
from sherwood.errors import error_handler
from sherwood.messages import *
from sherwood.models import to_dict, BaseModel as Base, User
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session as SqlAlchemyOrmSession
from typing import Annotated

logging.basicConfig(level=logging.DEBUG)

_ACCESS_TOKEN_DURATION_HOURS = 4

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


@router.websocket("/validate-password")
async def validate_password_websocket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            password = await ws.receive_text()
            reasons = validate_password(password)
            await ws.send_json({"reasons": reasons})
    except WebSocketDisconnect:
        logging.info("validate password websocket client disconnected")


@router.post("/sign-up")
async def post_sign_up(request: SignUpRequest, db: Database) -> SignUpResponse:
    try:
        sign_up_user(db, request.email, request.display_name, request.password)
        return SignUpResponse(redirect_url="/sherwood/sign-in.html")
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
async def post_sign_in(db: Database, request: SignInRequest) -> SignInResponse:
    try:
        token_type = "Bearer"
        access_token = sign_in_user(
            db,
            request.email,
            request.password,
            access_token_duration_hours=_ACCESS_TOKEN_DURATION_HOURS,
        )
        response = SignInResponse(
            token_type=token_type,
            access_token=access_token,
            redirect_url="/sherwood/profile.html",
        )
        return response

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


@router.post("/buy")
async def post_buy(
    request: BuyRequest, db: Database, user: AuthorizedUser
) -> BuyResponse:
    try:
        buy_portfolio_holding(db, user.portfolio.id, request.symbol, request.dollars)
        return BuyResponse()
    except (
        errors.InternalServerError,
        errors.MissingPortfolioError,
        errors.DuplicatePortfolioError,
        errors.InsufficientCashError,
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
        errors.InternalServerError,
        errors.MissingPortfolioError,
        errors.DuplicatePortfolioError,
        errors.InsufficientHoldingsError,
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
        errors.RequestValueError,
        errors.InternalServerError,
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
        errors.RequestValueError,
        errors.InternalServerError,
        errors.InsufficientHoldingsError,
    ):
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to divest from portfolio. Request: {request}. Error: {exc}."
        ) from exc


from concurrent.futures import ProcessPoolExecutor, as_completed
from pydantic import BaseModel
from sherwood.broker import market_data_provider
from sherwood.models import to_dict, Portfolio
from typing import Any


class LeaderboardRequest(BaseModel):
    sort_by: str


class LeaderboardResponse(BaseModel):
    portfolios: list[dict[str, Any]]


def _process_portfolio(portfolio):
    portfolio = to_dict(portfolio)
    user_ownership = [
        ownership
        for ownership in portfolio["ownership"]
        if ownership["owner_id"] == portfolio["id"]
    ][0]
    portfolio["cost"] = 0
    portfolio["value"] = 0
    for holding in portfolio["holdings"]:
        holding["value"] = (
            user_ownership["percent"]
            * holding["units"]
            * market_data_provider.get_price(holding["symbol"])
        )
        portfolio["cost"] += holding["cost"]
        portfolio["value"] += holding["value"]

    return portfolio


@router.post("/leaderboard")
async def get_leaderboard(request: LeaderboardRequest, db: Database):
    portfolios = db.query(Portfolio).all()
    symbols = {h.symbol for p in portfolios for h in p.holdings}
    market_data_provider.prefetch_prices(list(symbols))
    portfolios = [_process_portfolio(p) for p in portfolios]
    if request.sort_by == "gain_or_loss":
        portfolios = sorted(
            portfolios,
            key=lambda p: p["value"] - p["cost"],
        )
    return LeaderboardResponse(portfolios=portfolios)


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
        load_dotenv("/root/.env", override=True)  # TODO: self.cfg.get("env_file")
        postgresql_database_password = os.environ.get(
            POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME
        )
        if not postgresql_database_password:
            raise RuntimeError(
                f"Environment variable '{POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME}' is not set."
            )
        postgresql_database_url = URL.create(
            drivername="postgresql",
            username="sherwood",
            password=postgresql_database_password,
            host="sql.joemckenna.xyz",
            port=5432,
            database="sherwood",
            query={"sslmode": "require"},
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

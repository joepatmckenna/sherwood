from datetime import datetime
from fastapi import APIRouter, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from functools import wraps
import json
import logging
from pydantic import BaseModel
from sherwood.auth import (
    validate_password,
    AuthorizedUser,
    CookieSecurity,
    AUTHORIZATION_COOKIE_NAME,
)
from sherwood.broker import (
    get_portfolio,
    sign_up_user,
    sign_in_user,
    buy_portfolio_holding,
    sell_portfolio_holding,
    invest_in_portfolio,
    divest_from_portfolio,
)
from sherwood.db import Database
from sherwood.errors import *
from sherwood.market_data import get_prices
from sherwood.messages import *
from sherwood.models import has_expired, to_dict, upsert_blob, Blob, Ownership, User
from sqlalchemy.orm import Session
from typing import Any


ACCESS_TOKEN_LIFESPAN_HOURS = 4

api_router = APIRouter(prefix="/api")


class Cache:
    """Decorator for caching request/response pairs in the db.

    Example usage:

      @api_router.post("/fake")
      @cache(lifetime_seconds=10)
      async def api_fake(request: FakeRequest, db: Database) -> FakeResponse:
          return FakeResponse(...)

      where:
       - FakeRequest / FakeResponse are descendents of BaseModel
       - db is a sqlalchemy.orm.Session
    """

    def __init__(self, lifetime_seconds: int):
        self._lifetime_seconds = lifetime_seconds

    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> BaseModel:
            request = kwargs.get("request")
            request_type = type(request)
            if not BaseModel in request_type.__mro__:
                raise InternalServerError(f"BaseModel not in request mro: {request}.")
            if not isinstance(db := kwargs.get("db"), Session):
                raise InternalServerError(f"db is not a sqlalchemy.orm.Session: {db}.")

            key = f"{request_type}({request.model_dump_json()})"

            blob = db.get(Blob, key)
            if blob is None or has_expired(blob, self._lifetime_seconds):
                result = await func(*args, **kwargs)
                value = result.model_dump_json()
                blob = upsert_blob(db, key, value)

            return_type = func.__annotations__.get("return")
            if isinstance(return_type, type) and BaseModel in return_type.__mro__:
                return return_type.model_validate_json(blob.value)

            logging.info("cache not validating response type")
            return json.loads(blob.value)

        return wrapper


cache = Cache


@api_router.websocket("/validate-password")
async def validate_password_websocket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            password = await ws.receive_text()
            reasons = validate_password(password)
            await ws.send_json({"reasons": reasons})
    except WebSocketDisconnect:
        logging.info("validate password websocket client disconnected")


@api_router.post("/sign-up")
async def post_sign_up(request: SignUpRequest, db: Database) -> SignUpResponse:
    try:
        sign_up_user(db, request.email, request.display_name, request.password)
        return SignUpResponse(redirect_url="/sherwood/sign-in")
    except (
        DuplicateUserError,
        InternalServerError,
    ):
        raise
    except Exception as exc:
        raise InternalServerError(
            f"Failed to sign up user. Request: {request}. Error: {exc}."
        )


@api_router.post("/sign-in")
async def post_sign_in(
    request: SignInRequest, db: Database, secure: CookieSecurity
) -> SignInResponse:
    try:
        token_type = "Bearer"
        access_token = sign_in_user(
            db,
            request.email,
            request.password,
            access_token_duration_hours=ACCESS_TOKEN_LIFESPAN_HOURS,
        )
        response = JSONResponse(
            content=SignInResponse(
                redirect_url="/sherwood/profile",
            ).model_dump(),
        )
        response.set_cookie(
            key=AUTHORIZATION_COOKIE_NAME,
            value=f"{token_type} {access_token}",
            max_age=ACCESS_TOKEN_LIFESPAN_HOURS * 3600,
            httponly=True,
            secure=secure,
        )
        return response
    except (
        DuplicateUserError,
        IncorrectPasswordError,
        InternalServerError,
        MissingUserError,
    ):
        raise
    except Exception as exc:
        raise InternalServerError(
            f"Failed to sign in user. Request: {request}. Error: {exc}."
        )


@api_router.post("/sign-out")
async def api_sign_out(response: Response):
    response.delete_cookie(AUTHORIZATION_COOKIE_NAME)
    return {}


@api_router.get("/user")
async def get_user(user: AuthorizedUser):
    try:
        return to_dict(user)
    except (
        InvalidAccessTokenError,
        MissingUserError,
    ):
        raise
    except Exception as exc:
        raise InternalServerError(
            f"Failed to get user from X-Sherwood-Authorization header. Error: {exc}."
        )


@api_router.get("/user/{user_id}")
async def get_user_by_id(db: Database, user_id: int):
    try:
        return to_dict(db.get(User, user_id))
    except Exception as exc:
        raise InternalServerError(f"Failed to get user by ID. Error: {exc}.")


class PortfolioRequest(BaseModel):
    portfolio_id: int


class PortfolioResponse(BaseModel):
    portfolio: dict[str, Any]


@api_router.post("/portfolio")
async def post_api_portfolio(
    db: Database, request: PortfolioRequest
) -> PortfolioResponse:
    try:
        return PortfolioResponse(portfolio=get_portfolio(db, request.portfolio_id))
    except Exception as exc:
        raise InternalServerError(
            f"Failed to detect user from X-Sherwood-Authorization header. Error: {exc}."
        )


@api_router.get("/user/{user_id}")
async def get_user_by_id(user_id: int, db: Database):
    try:
        return to_dict(db.get(User, user_id))
    except Exception as exc:
        raise InternalServerError(
            f"Failed to detect user from X-Sherwood-Authorization header. Error: {exc}."
        )


@api_router.post("/buy")
async def post_buy(
    request: BuyRequest, db: Database, user: AuthorizedUser
) -> BuyResponse:
    try:
        buy_portfolio_holding(db, user.portfolio.id, request.symbol, request.dollars)
        return BuyResponse()
    except (
        InternalServerError,
        MissingPortfolioError,
        DuplicatePortfolioError,
        InsufficientCashError,
    ):
        raise
    except Exception as exc:
        raise InternalServerError(
            f"Failed to buy holding. Request: {request}. Error: {exc}."
        ) from exc


@api_router.post("/sell")
async def post_sell(
    request: SellRequest, db: Database, user: AuthorizedUser
) -> BuyResponse:
    try:
        sell_portfolio_holding(db, user.portfolio.id, request.symbol, request.dollars)
        return SellResponse()
    except (
        InternalServerError,
        MissingPortfolioError,
        DuplicatePortfolioError,
        InsufficientHoldingsError,
    ):
        raise
    except Exception as exc:
        raise InternalServerError(
            f"Failed to sell holding. Request: {request}. Error: {exc}."
        ) from exc


@api_router.post("/invest")
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
        RequestValueError,
        InternalServerError,
        InsufficientCashError,
        InsufficientHoldingsError,
    ):
        raise
    except Exception as exc:
        raise InternalServerError(
            f"Failed to invest in portfolio. Request: {request}. Error: {exc}."
        ) from exc


@api_router.post("/divest")
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
        RequestValueError,
        InternalServerError,
        InsufficientHoldingsError,
    ):
        raise
    except Exception as exc:
        raise InternalServerError(
            f"Failed to divest from portfolio. Request: {request}. Error: {exc}."
        ) from exc


def _lifetime_return(db, user):
    price_by_symbol = get_prices(
        db, [holding.symbol for holding in user.portfolio.holdings]
    )
    value = cost = user.portfolio.cash
    if user.portfolio.holdings:
        self_ownership = db.get(Ownership, (user.portfolio.id, user.id))
        if self_ownership is None:
            raise InternalServerError("Invalid portfolio ownership info.")
        value += self_ownership.percent * sum(
            holding.units * price_by_symbol[holding.symbol]
            for holding in user.portfolio.holdings
        )
        cost += sum(
            holding.cost for holding in user.portfolio.holdings
        )  # should add up to STARTING_BALANCE
    return value - cost


def _average_daily_return(db, user):
    lifetime_return = _lifetime_return(db, user)
    days = max(1, (datetime.now() - user.created_at).days)
    return lifetime_return / days


def _assets_under_management(db, user):
    price_by_symbol = get_prices(
        db, [holding.symbol for holding in user.portfolio.holdings]
    )
    return user.portfolio.cash + sum(
        holding.units * price_by_symbol[holding.symbol]
        for holding in user.portfolio.holdings
    )


@api_router.post("/leaderboard")
@cache(lifetime_seconds=60)
async def api_leaderboard_post(
    request: LeaderboardRequest, db: Database
) -> LeaderboardResponse:
    users = db.query(User).all()
    if request.sort_by == LeaderboardSortBy.LIFETIME_RETURN:
        key_fn = _lifetime_return
    elif request.sort_by == LeaderboardSortBy.AVERAGE_DAILY_RETURN:
        key_fn = _average_daily_return
    elif request.sort_by == LeaderboardSortBy.ASSETS_UNDER_MANAGEMENT:
        key_fn = _assets_under_management
    else:
        raise InternalServerError("unrecognized sort by")

    users = [(key_fn(db, user), user) for user in users]
    users.sort(key=lambda x: x[0], reverse=True)

    response = LeaderboardResponse(rows=[])
    for key, user in users:
        row = LeaderboardRow(user_id=user.id, user_display_name=user.display_name)
        setattr(row, request.sort_by.value, key)
        response.rows.append(row)

    return response


class UserHoldingsRequest(BaseModel):
    user_id: int


class UserHoldingsResponse(BaseModel):
    class UserHoldingsRow(BaseModel):
        symbol: str
        units: float
        value: float
        lifetime_return: float
        lifetime_return_percent: float

    rows: list[UserHoldingsRow]


@api_router.post("/user-holdings")
@cache(lifetime_seconds=10)
async def api_user_holdings(
    request: UserHoldingsRequest, db: Database
) -> UserHoldingsResponse:
    response = UserHoldingsResponse(rows=[])

    user = db.get(User, request.user_id)
    if user is None:
        raise MissingUserError(request.user_id)

    holdings = user.portfolio.holdings
    if not holdings:
        return response

    self_ownership = db.get(Ownership, (user.portfolio.id, user.id))
    if self_ownership is None:
        raise InternalServerError("Invalid portfolio ownership info.")

    price_by_symbol = get_prices(db, [holding.symbol for holding in holdings])

    for holding in holdings:
        symbol = holding.symbol
        units = holding.units * self_ownership.percent
        value = price_by_symbol[symbol] * units
        cost = holding.cost
        lifetime_return = value - cost
        lifetime_return_percent = lifetime_return / cost
        row = UserHoldingsResponse.UserHoldingsRow(
            symbol=symbol,
            units=units,
            value=value,
            lifetime_return=lifetime_return,
            lifetime_return_percent=lifetime_return_percent,
        )
        response.rows.append(row)

    return response

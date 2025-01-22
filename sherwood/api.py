from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import json
import logging
from sherwood.auth import validate_password, AuthorizedUser, AUTHORIZATION_COOKIE_NAME
from sherwood.broker import (
    sign_up_user,
    sign_in_user,
    buy_portfolio_holding,
    sell_portfolio_holding,
    invest_in_portfolio,
    divest_from_portfolio,
    upsert_leaderboard,
)
from sherwood.db import Database
from sherwood.errors import *
from sherwood.messages import *
from sherwood.models import has_expired, to_dict, Blob, User

ACCESS_TOKEN_DURATION_HOURS = 4

api_router = APIRouter(prefix="/api")


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
async def post_sign_in(db: Database, request: SignInRequest) -> SignInResponse:
    try:
        token_type = "Bearer"
        access_token = sign_in_user(
            db,
            request.email,
            request.password,
            access_token_duration_hours=ACCESS_TOKEN_DURATION_HOURS,
        )
        response = JSONResponse(
            content=SignInResponse(
                redirect_url="/sherwood/profile",
            ).model_dump(),
        )
        response.set_cookie(
            key=AUTHORIZATION_COOKIE_NAME,
            value=f"{token_type} {access_token}",
            max_age=ACCESS_TOKEN_DURATION_HOURS * 3600,
            httponly=True,
            secure=True,
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


from fastapi import Response


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


from typing import Any
from pydantic import BaseModel
from sherwood.broker import get_portfolio


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


def _upsert_blob(db, request, latency) -> Blob:
    key = repr(request)
    blob = db.get(Blob, key)
    if not (blob is None or has_expired(blob, latency)):
        return blob
    if isinstance(request, LeaderboardBlobRequest):
        return upsert_leaderboard(db, request)
    else:
        raise InternalServerError(f"Unrecognized blob request type {request}")


@api_router.post("/blob")
async def upsert_blob(
    request: BlobRequest, db: Database, latency: int = 10
) -> BlobResponse:
    try:
        blob = _upsert_blob(db, request.oneof(), latency)
        return BlobResponse(value=json.loads(blob.value))
    except (
        RequestValueError,
        InternalServerError,
    ):
        raise
    except Exception as exc:
        raise InternalServerError(
            f"Failed to get blob. Request: {request}. Error: {exc}."
        ) from exc


### leaderboard endpoing ###
# todo: blob_caching decorator

from datetime import datetime
from enum import Enum
from sherwood.models import Ownership
from sherwood.market_data import get_prices


class LeaderboardSortBy(Enum):
    LIFETIME_RETURN = "lifetime_return"
    AVERAGE_DAILY_RETURN = "average_daily_return"
    ASSETS_UNDER_MANAGEMENT = "assets_under_management"


class LeaderboardRequest(BaseModel):
    top_k: int
    sort_by: LeaderboardSortBy


class LeaderboardRow(BaseModel):
    user_id: int
    user_display_name: str
    lifetime_return: float | None = None
    average_daily_return: float | None = None
    assets_under_management: float | None = None


class LeaderboardResponse(BaseModel):
    rows: list[LeaderboardRow]


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
async def api_post_leaderboard(
    request: LeaderboardRequest,
    db: Database,
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

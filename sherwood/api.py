from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
import logging
from sherwood import errors
from sherwood.auth import validate_password
from sherwood.broker import (
    create_leaderboard,
    enrich_user_with_price_info,
    sign_up_user,
    sign_in_user,
    buy_portfolio_holding,
    sell_portfolio_holding,
    invest_in_portfolio,
    divest_from_portfolio,
)
from sherwood.dependencies import AuthorizedUser, Database, AUTHORIZATION_COOKIE_NAME
from sherwood.messages import *
from sherwood.models import (
    has_expired,
    to_dict,
    Blob,
    User,
)


ACCESS_TOKEN_DURATION_HOURS = 4
LEADERBOARD_REFRESH_RATE_SECONDS = 60

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
                redirect_url="/sherwood/",
            ).model_dump(),
        )
        response.set_cookie(
            key=AUTHORIZATION_COOKIE_NAME,
            value=f"{token_type} {access_token}",
            max_age=ACCESS_TOKEN_DURATION_HOURS * 3600,
            httponly=True,
            # secure=True,
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


@api_router.get("/user")
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


@api_router.get("/user/{user_id}")
async def get_user_by_id(user_id: int, db: Database):
    try:
        return enrich_user_with_price_info(db.get(User, user_id))
    except Exception as exc:
        raise errors.InternalServerError(
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


@api_router.post("/sell")
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
        errors.RequestValueError,
        errors.InternalServerError,
        errors.InsufficientHoldingsError,
    ):
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to divest from portfolio. Request: {request}. Error: {exc}."
        ) from exc


@api_router.post("/leaderboard")
async def get_leaderboard(
    request: LeaderboardRequest, db: Database
) -> LeaderboardResponse:
    try:
        blob = db.get(Blob, repr(request))
        if blob is None or has_expired(blob, LEADERBOARD_REFRESH_RATE_SECONDS):
            blob = create_leaderboard(db, request)
        return LeaderboardResponse.model_validate_json(blob.value)
    except errors.InternalServerError:
        raise
    except Exception as exc:
        raise errors.InternalServerError(
            f"Failed to get leaderboard. Request: {request}. Error: {exc}."
        ) from exc

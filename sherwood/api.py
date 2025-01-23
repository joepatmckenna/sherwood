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
from sqlalchemy import func
from sherwood.auth import generate_access_token, password_context
from sherwood.broker import (
    buy_portfolio_holding,
    sell_portfolio_holding,
    invest_in_portfolio,
    divest_from_portfolio,
    STARTING_BALANCE,
)
from sherwood.db import maybe_commit, Database
from sherwood.errors import *
from sherwood.market_data import get_prices
from sherwood.messages import *
from sherwood.models import (
    create_user,
    has_expired,
    to_dict,
    upsert_blob,
    Blob,
    Ownership,
    User,
)
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.orm import Session

api_router = APIRouter(prefix="/api")

ACCESS_TOKEN_LIFESPAN_HOURS = 4


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

    def __call__(self, f):
        @wraps(f)
        async def wrapper(*args, **kwargs) -> BaseModel:
            request = kwargs.get("request")
            if request is None:
                raise InternalServerError(f"missing request kwarg.")
            request_type = type(request)
            if not BaseModel in request_type.__mro__:
                raise InternalServerError(f"BaseModel not in request mro: {request}.")
            if not isinstance(db := kwargs.get("db"), Session):
                raise InternalServerError(f"db is not a sqlalchemy.orm.Session: {db}.")

            key = f"{request_type}({request.model_dump_json()})"

            blob = db.get(Blob, key)
            if blob is None or has_expired(blob, self._lifetime_seconds):
                result = await f(*args, **kwargs)
                value = result.model_dump_json()
                blob = upsert_blob(db, key, value)

            return_type = f.__annotations__.get("return")
            if isinstance(return_type, type) and BaseModel in return_type.__mro__:
                return return_type.model_validate_json(blob.value)

            logging.info("cache not validating response type")
            return json.loads(blob.value)

        return wrapper


class HandleErrors:
    def __init__(self, expected_error_types: tuple[SherwoodError]):
        self._expected_error_types = expected_error_types

    def __call__(self, f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            try:
                return await f(*args, **kwargs)
            except self._expected_error_types:
                raise
            except Exception as exc:
                raise InternalServerError(
                    f"Unexpected error (func={f}, args={args}, kwargs={kwargs}, error={repr(exc)})"
                ) from exc

        return wrapper


cache = Cache
handle_errors = HandleErrors

###################################################
# user account routes


@api_router.post("/sign-up")
@handle_errors(
    (
        DuplicateUserError,
        InternalServerError,
    )
)
async def api_sign_up_post(request: SignUpRequest, db: Database) -> SignUpResponse:

    if db.query(User).filter_by(email=request.email).first() is not None:
        raise DuplicateUserError(email=request.email)
    if (
        db.query(User)
        .filter(func.lower(User.display_name) == request.display_name.lower())
        .first()
        is not None
    ):
        raise DuplicateUserError(display_name=request.display_name)
    create_user(
        db=db,
        email=request.email,
        display_name=request.display_name,
        password=request.password,
        cash=STARTING_BALANCE,
    )
    return SignUpResponse(redirect_url="/sherwood/sign-in")


@api_router.post("/sign-in")
@handle_errors(
    (
        DuplicateUserError,
        IncorrectPasswordError,
        InternalServerError,
        MissingUserError,
    )
)
async def api_sign_in_post(
    request: SignInRequest, db: Database, secure: CookieSecurity
) -> SignInResponse:
    try:
        user = db.query(User).filter_by(email=request.email).one_or_none()
    except MultipleResultsFound:
        raise DuplicateUserError(email=request.email)
    if user is None:
        raise MissingUserError(email=request.email)
    if not password_context.verify(request.password, user.password):
        raise IncorrectPasswordError()
    if password_context.needs_update(user.password):
        user.password = password_context.hash(user.password)
        maybe_commit(db, "Failed to update password hash.")
    access_token = generate_access_token(user, ACCESS_TOKEN_LIFESPAN_HOURS)
    response = SignInResponse(redirect_url="/sherwood/profile")
    response = JSONResponse(content=response.model_dump())
    response.set_cookie(
        key=AUTHORIZATION_COOKIE_NAME,
        value=f"Bearer {access_token}",
        max_age=ACCESS_TOKEN_LIFESPAN_HOURS * 3600,
        httponly=True,
        secure=secure,
    )
    return response


@api_router.post("/sign-out")
@handle_errors(tuple())
async def api_sign_out_post(response: Response):
    response.delete_cookie(AUTHORIZATION_COOKIE_NAME)
    return {}


@api_router.get("/user")
@handle_errors(
    (
        InvalidAccessTokenError,
        MissingUserError,
    )
)
async def api_user_get(user: AuthorizedUser):
    return to_dict(user)


@api_router.get("/user/{user_id}")
@handle_errors(tuple())
async def api_user_user_id_get(db: Database, user_id: int):
    return to_dict(db.get(User, user_id))


###################################################
# broker routes


@api_router.post("/buy")
@handle_errors(
    (
        DuplicatePortfolioError,
        InsufficientCashError,
        InternalServerError,
        InvalidAccessTokenError,
        MissingPortfolioError,
        MissingUserError,
    )
)
async def api_buy_post(
    request: BuyRequest, db: Database, user: AuthorizedUser
) -> BuyResponse:
    buy_portfolio_holding(db, user.portfolio.id, request.symbol, request.dollars)
    return BuyResponse()


@api_router.post("/sell")
@handle_errors(
    (
        DuplicatePortfolioError,
        InsufficientHoldingsError,
        InternalServerError,
        InvalidAccessTokenError,
        MissingPortfolioError,
        MissingUserError,
    )
)
async def api_sell_post(
    request: SellRequest, db: Database, user: AuthorizedUser
) -> BuyResponse:
    sell_portfolio_holding(db, user.portfolio.id, request.symbol, request.dollars)
    return SellResponse()


@api_router.post("/invest")
@handle_errors(
    (
        InsufficientCashError,
        InsufficientHoldingsError,
        InternalServerError,
        InvalidAccessTokenError,
        MissingUserError,
        RequestValueError,
    )
)
async def api_invest_post(
    request: InvestRequest, db: Database, user: AuthorizedUser
) -> InvestResponse:
    invest_in_portfolio(
        db,
        request.investee_portfolio_id,
        user.portfolio.id,
        request.dollars,
    )
    return InvestResponse()


@api_router.post("/divest")
@handle_errors(
    (
        InsufficientHoldingsError,
        InternalServerError,
        InvalidAccessTokenError,
        MissingUserError,
        RequestValueError,
    )
)
async def api_divest_post(
    request: DivestRequest, db: Database, user: AuthorizedUser
) -> DivestResponse:
    divest_from_portfolio(
        db,
        request.investee_portfolio_id,
        user.portfolio.id,
        request.dollars,
    )
    return DivestResponse()


###################################################
# websocket


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


###################################################
# in development


def _lifetime_return(db, user):
    price_by_symbol = get_prices(
        db, [holding.symbol for holding in user.portfolio.holdings]
    )
    value = cost = user.portfolio.cash
    if user.portfolio.holdings:
        self_ownership = db.get(Ownership, (user.portfolio.id, user.id))
        if self_ownership is None:
            raise MissingOwnershipError(user.portfolio.id, user.id)
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
@handle_errors((InternalServerError,))
async def api_leaderboard_post(
    request: LeaderboardRequest, db: Database
) -> LeaderboardResponse:
    users = db.query(User).all()
    sort_by = request.sort_by
    LeaderboardSortBy = LeaderboardRequest.LeaderboardSortBy
    if sort_by == LeaderboardSortBy.LIFETIME_RETURN:
        key_fn = _lifetime_return
    elif sort_by == LeaderboardSortBy.AVERAGE_DAILY_RETURN:
        key_fn = _average_daily_return
    elif sort_by == LeaderboardSortBy.ASSETS_UNDER_MANAGEMENT:
        key_fn = _assets_under_management
    else:
        raise RequestValueError(f"unrecognized sort by: {sort_by}")

    users = [(key_fn(db, user), user) for user in users]
    users.sort(key=lambda x: x[0], reverse=True)
    response = LeaderboardResponse(rows=[])
    for key, user in users:
        row = LeaderboardResponse.LeaderboardRow(
            user_id=user.id, user_display_name=user.display_name
        )
        setattr(row, request.sort_by.value, key)
        response.rows.append(row)

    return response


@api_router.post("/user-holdings")
@cache(lifetime_seconds=10)
@handle_errors(
    (
        InternalServerError,
        MissingUserError,
    )
)
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
        raise MissingOwnershipError(user.portfolio.id, user.id)

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

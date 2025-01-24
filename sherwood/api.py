from datetime import datetime
from fastapi import APIRouter, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import logging
from sherwood.auth import (
    validate_display_name,
    validate_password,
    AuthorizedUser,
    CookieSecurity,
    ACCESS_TOKEN_LIFESPAN_HOURS,
    AUTHORIZATION_COOKIE_NAME,
)
from sherwood.broker import (
    buy_portfolio_holding,
    sell_portfolio_holding,
    invest_in_portfolio,
    divest_from_portfolio,
)
from sherwood.caching import Cache as cache
from sherwood.db import Database
from sherwood.errors import *
from sherwood.error_handling import HandleErrors as handle_errors
from sherwood.market_data import get_prices
from sherwood.messages import *
from sherwood.models import to_dict, Ownership, Portfolio, User
from sherwood.registrar import sign_up_user, sign_in_user

api_router = APIRouter(prefix="/api")


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
    sign_up_user(db, request.email, request.display_name, request.password)
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
    access_token = sign_in_user(db, request.email, request.password)
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
# websockets


@api_router.websocket("/validate-display-name")
async def api_validate_display_name_websocket(web_socket: WebSocket):
    await web_socket.accept()
    try:
        while True:
            display_name = await web_socket.receive_text()
            reasons = validate_display_name(display_name)
            await web_socket.send_json({"reasons": reasons})
    except WebSocketDisconnect:
        logging.info("validate display_name client disconnected")


@api_router.websocket("/validate-password")
async def api_validate_password_websocket(web_socket: WebSocket):
    await web_socket.accept()
    try:
        while True:
            password = await web_socket.receive_text()
            reasons = validate_password(password)
            await web_socket.send_json({"reasons": reasons})
    except WebSocketDisconnect:
        logging.info("validate password client disconnected")


###################################################
# in development


def _portfolio_lifetime_return(db, portfolio):
    price_by_symbol = get_prices(db, [holding.symbol for holding in portfolio.holdings])
    cost = value = portfolio.cash
    if portfolio.holdings:
        self_ownership = db.get(Ownership, (portfolio.id, portfolio.id))
        if self_ownership is None:
            raise MissingOwnershipError(portfolio.id, portfolio.id)
        cost += sum(
            holding.cost for holding in portfolio.holdings
        )  # should add up to STARTING_BALANCE
        value += self_ownership.percent * sum(
            holding.units * price_by_symbol[holding.symbol]
            for holding in portfolio.holdings
        )
    return value - cost


def _portfolio_average_daily_return(db, portfolio):
    average_daily_return = _portfolio_lifetime_return(db, portfolio)
    days = (datetime.now() - portfolio.created_at).days
    if days > 0:
        average_daily_return /= days
    return average_daily_return


def _assets_under_management(db, user):
    price_by_symbol = get_prices(
        db, [holding.symbol for holding in user.portfolio.holdings]
    )
    return user.portfolio.cash + sum(
        holding.units * price_by_symbol[holding.symbol]
        for holding in user.portfolio.holdings
    )


@api_router.post("/leaderboard")
@cache(lifetime_seconds=300)
@handle_errors(
    (
        InternalServerError,
        RequestValueError,
    )
)
async def api_leaderboard_post(
    request: LeaderboardRequest, db: Database
) -> LeaderboardResponse:
    if request.sort_by not in request.columns:
        raise RequestValueError("sort_by not in columns")

    Column = LeaderboardRequest.Column
    column_fns = {
        Column.LIFETIME_RETURN: lambda user: _portfolio_lifetime_return(
            db, user.portfolio
        ),
        Column.AVERAGE_DAILY_RETURN: lambda user: _portfolio_average_daily_return(
            db, user.portfolio
        ),
        Column.ASSETS_UNDER_MANAGEMENT: lambda user: _assets_under_management(db, user),
    }

    response = LeaderboardResponse(rows=[])
    for user in db.query(User).all():
        row = LeaderboardResponse.Row(
            user_id=user.id,
            user_display_name=user.display_name,
            portfolio_id=user.portfolio.id,
            columns={},
        )
        for column in request.columns:
            row.columns[column] = column_fns[column](user)
        response.rows.append(row)

    response.rows.sort(key=lambda row: row.columns[request.sort_by], reverse=True)
    return response


@api_router.post("/portfolio-holdings")
@cache(lifetime_seconds=300)
@handle_errors(
    (
        InternalServerError,
        MissingOwnershipError,
        MissingPortfolioError,
        MissingUserError,
        RequestValueError,
    )
)
async def api_portfolio_holdings_post(
    request: PortfolioHoldingsRequest, db: Database
) -> PortfolioHoldingsResponse:
    if request.sort_by not in request.columns:
        raise RequestValueError("sort_by not in columns")

    portfolio = db.get(Portfolio, request.portfolio_id)
    if portfolio is None:
        raise MissingPortfolioError(request.portfolio_id)

    response = PortfolioHoldingsResponse(rows=[])
    if not portfolio.holdings:
        return response

    self_ownership = db.get(Ownership, (portfolio.id, portfolio.id))
    if self_ownership is None:
        raise MissingOwnershipError(portfolio.id, portfolio.id)

    price_by_symbol = get_prices(db, [holding.symbol for holding in portfolio.holdings])

    Column = PortfolioHoldingsRequest.Column
    column_fns = {
        Column.UNITS: lambda h: h.units,
        Column.PRICE: lambda h: price_by_symbol[h.symbol],
        Column.VALUE: lambda h: (
            h.units * price_by_symbol[h.symbol] * self_ownership.percent
        ),
        Column.LIFETIME_RETURN: lambda h: (
            h.units * price_by_symbol[h.symbol] * self_ownership.percent - h.cost
        ),
        Column.AVERAGE_DAILY_RETURN: lambda h: (
            (h.units * price_by_symbol[h.symbol] * self_ownership.percent - h.cost)
            / max(1, (datetime.now() - holding.created_at).days)
        ),
    }

    for holding in portfolio.holdings:
        row = PortfolioHoldingsResponse.Row(symbol=holding.symbol, columns={})
        for column in request.columns:
            row.columns[column] = column_fns[column](holding)
        response.rows.append(row)

    response.rows.sort(key=lambda row: row.columns[request.sort_by], reverse=True)
    return response


@api_router.post("/portfolio-investors")
@cache(lifetime_seconds=300)
@handle_errors(
    (
        InternalServerError,
        MissingPortfolioError,
        RequestValueError,
    )
)
async def api_portfolio_investors_post(
    request: PortfolioInvestorsRequest, db: Database
) -> PortfolioInvestorsResponse:
    if request.sort_by not in request.columns:
        raise RequestValueError("sort_by not in columns")

    portfolio = db.get(Portfolio, request.portfolio_id)
    if portfolio is None:
        raise MissingPortfolioError(request.portfolio_id)

    response = PortfolioInvestorsResponse(rows=[])
    ownership = [o for o in portfolio.ownership if o.owner_id != portfolio.id]
    if not ownership:
        return response

    user_ids = [o.owner_id for o in ownership]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    display_name_by_id = {user.id: user.display_name for user in users}

    price_by_symbol = get_prices(db, [holding.symbol for holding in portfolio.holdings])
    portfolio_value = sum(
        holding.units * price_by_symbol[holding.symbol]
        for holding in portfolio.holdings
    )

    Column = PortfolioInvestorsRequest.Column
    column_fns = {
        Column.AMOUNT_INVESTED: lambda o: o.cost,
        Column.VALUE: lambda o: portfolio_value * o.percent,
        Column.LIFETIME_RETURN: lambda o: portfolio_value * o.percent - o.cost,
        Column.AVERAGE_DAILY_RETURN: lambda o: (
            (portfolio_value * o.percent - o.cost)
            / max(1, (datetime.now() - o.created_at).days)
        ),
    }

    for o in ownership:
        row = PortfolioInvestorsResponse.Row(
            user_id=o.owner_id,
            user_display_name=display_name_by_id[o.owner_id],
            columns={},
        )
        for column in request.columns:
            row.columns[column] = column_fns[column](o)
        response.rows.append(row)

    response.rows.sort(key=lambda row: row.columns[request.sort_by], reverse=True)
    return response


@api_router.post("/user-investments")
@cache(lifetime_seconds=60)
@handle_errors((InternalServerError,))
async def api_user_investments_post(
    request: UserInvestmentsRequest, db: Database
) -> UserInvestmentsResponse:

    ownership = db.query(Ownership).filter_by(owner_id=request.user_id).all()

    ownership_by_portfolio_id = {
        o.portfolio_id: o for o in ownership if o.portfolio_id != request.user_id
    }

    response = UserInvestmentsResponse(rows=[])
    if not ownership_by_portfolio_id:
        return response

    user_ids = list(ownership_by_portfolio_id)
    users = db.query(User).filter(User.id.in_(user_ids)).all()

    symbols = set(
        [holding.symbol for user in users for holding in user.portfolio.holdings]
    )
    price_by_symbol = get_prices(db, list(symbols))

    Column = UserInvestmentsRequest.Column

    for user in users:
        row = UserInvestmentsResponse.Row(
            user_id=user.id,
            user_display_name=user.display_name,
            columns={},
        )

        portfolio_value = sum(
            holding.units * price_by_symbol[holding.symbol]
            for holding in user.portfolio.holdings
        )

        column_fns = {
            Column.AMOUNT_INVESTED: lambda o: o.cost,
            Column.VALUE: lambda o: portfolio_value * o.percent,
            Column.LIFETIME_RETURN: lambda o: portfolio_value * o.percent - o.cost,
            Column.AVERAGE_DAILY_RETURN: lambda o: (
                (portfolio_value * o.percent - o.cost)
                / max(1, (datetime.now() - o.created_at).days)
            ),
        }
        for column in request.columns:
            o = ownership_by_portfolio_id[user.portfolio.id]
            row.columns[column] = column_fns[column](o)
        response.rows.append(row)

    response.rows.sort(key=lambda row: row.columns[request.sort_by], reverse=True)
    return response

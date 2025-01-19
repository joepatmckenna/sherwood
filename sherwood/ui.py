from fastapi import APIRouter, Cookie, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import json
from sherwood.auth import authorized_user, AUTHORIZATION_COOKIE_NAME
from sherwood.broker import enrich_user_with_price_info
from sherwood.db import Database
from sherwood.errors import InvalidAccessTokenError, MissingUserError
from sherwood.models import to_dict
from typing import Annotated

ui_router = APIRouter(prefix="")

templates = Jinja2Templates(directory="ui/templates")


@ui_router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    db: Database,
    x_sherwood_authorization: Annotated[str | None, Cookie()] = None,
):
    try:
        user = await authorized_user(db, x_sherwood_authorization)
        user = enrich_user_with_price_info(db, user)
        return templates.TemplateResponse(
            request=request,
            name="profile.html",
            context={"user": json.dumps(user)},
        )
    except (
        InvalidAccessTokenError,
        MissingUserError,
    ):
        return templates.TemplateResponse(request=request, name="index.html")


@ui_router.get("/sign-up", response_class=HTMLResponse)
async def sign_up(request: Request):
    return templates.TemplateResponse(request=request, name="sign-up.html")


@ui_router.get("/sign-in", response_class=HTMLResponse)
async def sign_in(request: Request):
    return templates.TemplateResponse(request=request, name="sign-in.html")


@ui_router.get("/sign-out")
async def sign_in(request: Request):
    response = RedirectResponse(request.url_for("home"))
    response.delete_cookie(key=AUTHORIZATION_COOKIE_NAME)
    return response

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import json
from sherwood.dependencies import AuthorizedUser, AUTHORIZATION_COOKIE_NAME
from sherwood.broker import enrich_user_with_price_info

ui_router = APIRouter(prefix="")

templates = Jinja2Templates(directory="ui/templates")


@ui_router.get("/public", response_class=HTMLResponse)
async def public_home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@ui_router.get("/", response_class=HTMLResponse)
async def authorized_user_home(request: Request, user: AuthorizedUser):
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"user": json.dumps(enrich_user_with_price_info(user))},
    )


@ui_router.get("/sign-up", response_class=HTMLResponse)
async def sign_up(request: Request):
    return templates.TemplateResponse(request=request, name="sign-up.html")


@ui_router.get("/sign-in", response_class=HTMLResponse)
async def sign_in(request: Request):
    return templates.TemplateResponse(request=request, name="sign-in.html")


@ui_router.get("/sign-out")
async def sign_in(request: Request):
    response = RedirectResponse(request.url_for("public_home"))
    response.delete_cookie(key=AUTHORIZATION_COOKIE_NAME)
    return response

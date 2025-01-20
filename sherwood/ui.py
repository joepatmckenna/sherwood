from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sherwood.auth import AUTHORIZATION_COOKIE_NAME

ui_router = APIRouter(prefix="")

templates = Jinja2Templates(directory="ui/templates")


@ui_router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@ui_router.get("/sign-up", response_class=HTMLResponse)
async def sign_up(request: Request):
    return templates.TemplateResponse(request=request, name="sign-up.html")


@ui_router.get("/sign-in", response_class=HTMLResponse)
async def sign_in(request: Request):
    return templates.TemplateResponse(request=request, name="sign-in.html")


@ui_router.get("/sign-out")
async def sign_out(request: Request):
    response = RedirectResponse(request.url_for("home"))
    response.delete_cookie(key=AUTHORIZATION_COOKIE_NAME)
    return response


# @ui_router.get("/landing", response_class=HTMLResponse)
# async def profile(request: Request):
#     return templates.TemplateResponse(request=request, name="landing.html")


@ui_router.get("/profile", response_class=HTMLResponse)
async def authorized_user_profile(request: Request):
    return templates.TemplateResponse(request=request, name="profile.html")


@ui_router.get("/user/{user_id}", response_class=HTMLResponse)
async def user_page(request: Request, user_id: int):
    return templates.TemplateResponse(
        request=request, name="user.html", context={"user_id": user_id}
    )

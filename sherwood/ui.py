from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import glob
from sherwood.auth import AUTHORIZATION_COOKIE_NAME

ui_router = APIRouter(prefix="")

templates = Jinja2Templates(directory="ui")


@ui_router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "templates": [f.lstrip("ui/") for f in glob.glob("ui/src/templates/*.html")]
        },
    )

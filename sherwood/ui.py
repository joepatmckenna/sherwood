from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import glob

# from frozendict import frozendict

ui_router = APIRouter(prefix="")

templates = Jinja2Templates(directory="ui")
# TODO
# _TEMPLATES_BY_PATH = frozendict({})


@ui_router.get("{path:path}", response_class=HTMLResponse)
async def home(request: Request, path: str):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "templates": [
                f.lstrip("ui/") for f in glob.glob("ui/src/templates/*.html")
            ],
            # "templates": [f"ui/src/templates/{t}.html" for t in _TEMPLATES_BY_PATH.get(path, [])],
        },
    )

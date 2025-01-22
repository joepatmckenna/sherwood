from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import gunicorn.app.base
import logging
import os
from sherwood import errors
from sherwood.api import api_router
from sherwood.db import Session, POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME
from sherwood.errors import SherwoodError
from sherwood.models import BaseModel as Base
from sherwood.ui import ui_router
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

logging.basicConfig(level=logging.DEBUG)


async def error_handler(request: Request, exc: SherwoodError) -> JSONResponse:
    # if request.url.path.startswith("/api"):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"status_code": exc.status_code, "detail": exc.detail}},
        headers=exc.headers,
    )
    # return RedirectResponse(request.url_for("home"))


def create_app(*args, **kwargs):
    app = FastAPI(*args, **kwargs)
    # app.mount("/static", StaticFiles(directory="ui/static"), name="static")
    app.mount("/ui", StaticFiles(directory="ui"), name="ui")
    app.include_router(api_router)
    app.include_router(ui_router)
    for error in errors.SherwoodError.__subclasses__():
        app.add_exception_handler(error, error_handler)
    return app


class App(gunicorn.app.base.BaseApplication):
    def load_config(self):
        opts = vars(self.cfg.parser().parse_args())
        for key, val in opts.items():
            if val is None:
                continue
            key = key.lower()
            if key in {"args", "worker_class"}:
                continue
            self.cfg.set(key, val)
        self.cfg.set(
            "worker_class",
            "uvicorn.workers.UvicornWorker",
        )
        if not opts.get("workers"):
            self.cfg.set("workers", 2 * os.cpu_count() + 1)

    def load(self):
        load_dotenv("/root/.env", override=True)  # TODO: self.cfg.get("env_file")
        postgresql_database_password = os.environ.get(
            POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME
        )
        if not postgresql_database_password:
            raise RuntimeError(
                f"Environment variable '{POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME}' is not set."
            )
        postgresql_database_url = URL.create(
            drivername="postgresql",
            username="sherwood",
            password=postgresql_database_password,
            host="sql.joemckenna.xyz",
            port=5432,
            database="sherwood",
            query={"sslmode": "require"},
        )
        engine = create_engine(postgresql_database_url)
        Session.configure(bind=engine)

        @asynccontextmanager
        async def lifespan(_):
            Base.metadata.create_all(engine)
            yield
            engine.dispose()

        return create_app(title="sherwood", version="0.0.0", lifespan=lifespan)


if __name__ == "__main__":
    App().run()

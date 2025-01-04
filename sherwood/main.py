from fastapi import status, Depends, FastAPI, Header, HTTPException
import gunicorn.app.base
import logging
import os
from pydantic import BaseModel, EmailStr
from sherwood import errors
from sherwood.auth import (
    decode_jwt_for_user,
    generate_jwt_for_user,
    password_context,
    validate_password,
)
from sherwood.db import get_db
from sherwood.models import create_user, to_dict, User
from sqlalchemy.orm import Session
from typing import Annotated


logging.basicConfig(level=logging.DEBUG)


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str


class SignUpResponse(BaseModel):
    jwt: str


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class SignInResponse(BaseModel):
    jwt: str


async def authorized_user_info(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict | None:
    try:
        token_type, _, jwt = authorization.partition(" ")
        assert token_type.strip().upper() == "BEARER"
        decode_jwt_for_user(jwt, user)
        user = db.query(User).filter_by(email=user).first()
        assert user is not None
        return {"jwt": jwt, "user": to_dict(user)}
    except:
        pass


def create_app(*args, **kwargs):
    app = FastAPI(*args, **kwargs)

    @app.post("/sign_up")
    async def sign_up(
        request: SignUpRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> SignUpResponse:
        user = db.query(User).filter_by(email=request.email).first()
        if user is not None:
            raise errors.DuplicateUserError(status.HTTP_409_CONFLICT, request.email)
        is_valid, reasons = validate_password(request.password)
        if not is_valid:
            raise errors.InvalidPasswordError(status.HTTP_400_BAD_REQUEST, reasons)
        try:
            user = create_user(db, request.email, request.password)
            return SignUpResponse(jwt=generate_jwt_for_user(user))
        except:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user.",
            )

    @app.post("/sign_in")
    async def sign_in(
        request: SignInRequest,
        db: Annotated[Session, Depends(get_db)],
        # user_info: Annotated[dict | None, Depends(authorized_user_info)] = None,
    ) -> SignInResponse:
        # if user_info is not None and ((jwt := user_info.get("jwt")) is not None):
        #     return SignInResponse(jwt=jwt)
        user = db.query(User).filter_by(email=request.email).first()
        if user is None:
            raise errors.MissingUserError(status.HTTP_404_NOT_FOUND, request.email)
        if not password_context.verify(request.password, user.password):
            raise errors.IncorrectPasswordError(status.HTTP_401_UNAUTHORIZED)
        if password_context.needs_update(user.password):
            user.password = password_context.hash(request.password)
            db.commit()
        return SignInResponse(jwt=generate_jwt_for_user(user))

    @app.get("/user")
    async def get_authorized_user(
        user_info: Annotated[dict | None, Depends(authorized_user_info)] = None,
    ):
        return user_info.get("user")

    for error in errors.errors:
        app.add_exception_handler(error, errors.error_handler)
    return app


app = create_app(title="sherwood", version="0.0.0")


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
            self.cfg.set("workers", os.cpu_count())

    def load(self):
        return app


if __name__ == "__main__":
    App().run()

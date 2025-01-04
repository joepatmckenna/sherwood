from dataclasses import dataclass, field
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import EmailStr


@dataclass
class SherwoodError(Exception):
    status_code: int


@dataclass
class InvalidPasswordError(SherwoodError):
    reasons: list[str]

    def __repr__(self):
        return " ".join(self.reasons)


@dataclass
class IncorrectPasswordError(SherwoodError):
    def __repr__(self):
        return "Login credentials don't match our records."


@dataclass
class MissingUserError(SherwoodError):
    email: EmailStr

    def __repr__(self):
        return f"User with email {self.email} not found."


@dataclass
class DuplicateUserError(SherwoodError):
    email: EmailStr

    def __repr__(self):
        return f"User with email {self.email} already exists."


async def error_handler(req: Request, exc: SherwoodError):
    return JSONResponse(status_code=exc.status_code, content={"message": str(exc)})


errors = (
    MissingUserError,
    DuplicateUserError,
    InvalidPasswordError,
    IncorrectPasswordError,
)

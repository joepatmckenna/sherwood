from dataclasses import dataclass, field
from fastapi import status, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import EmailStr


@dataclass
class SherwoodError(HTTPException):
    def __init__(self, status_code, detail, headers):
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers,
        )


class InternalServerError(SherwoodError):
    def __init__(self, detail, headers=None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            headers=headers,
        )


class InvalidPasswordError(SherwoodError):
    def __init__(self, reasons, headers=None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=" ".join(reasons),
            headers=headers,
        )


class IncorrectPasswordError(SherwoodError):
    def __init__(self, headers=None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login credentials don't match our records.",
            headers=headers,
        )


class InvalidAccessToken(SherwoodError):
    def __init__(self, detail):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid access token: {detail}",
            headers={"WWW-Authenticate": "Bearer"},
        )


class MissingUserError(SherwoodError):
    def __init__(
        self,
        user_id: str | None = None,
        email: str | None = None,
        headers=None,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Missing user"
            + ("" if user_id is None else f", user ID: {user_id}")
            + ("" if email is None else f", email: {email}")
            + ".",
            headers=headers,
        )


class DuplicateUserError(SherwoodError):
    def __init__(
        self,
        user_id: str | None = None,
        email: str | None = None,
        headers=None,
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already exists"
            + ("" if user_id is None else f", user ID: {user_id}")
            + ("" if email is None else f", email: {email}")
            + ".",
            headers=headers,
        )


class MissingPortfolioError(SherwoodError):
    def __init__(self, portfolio_id: str, headers=None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio with ID {portfolio_id} missing.",
            headers=headers,
        )


class DuplicatePortfolioError(SherwoodError):
    def __init__(self, portfolio_id: str):
        super().__init__(
            f"Multiple portfolios with ID {portfolio_id}.",
        )


class InsufficientCashError(SherwoodError):
    def __init__(self, needed: float, actual: float, headers=None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient cash, needed: {needed}, actual: {actual}.",
            headers=headers,
        )


class InsufficientHoldingsError(SherwoodError):
    def __init__(self, symbol, needed, actual, headers=None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient holdings of symbol {symbol}, needed: {needed}, actual: {actual}",
            headers=headers,
        )


class RequestValueError(SherwoodError):
    def __init__(self, detail=str, headers=None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            headers=headers,
        )


async def error_handler(req: Request, exc: SherwoodError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "status_code": exc.status_code,
                "detail": exc.detail,
            },
        },
        headers=exc.headers,
    )

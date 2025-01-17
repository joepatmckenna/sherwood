from fastapi import status, HTTPException


class SherwoodError(HTTPException):
    def __init__(self, status_code: int, detail, headers=None) -> None:
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers,
        )


class InternalServerError(SherwoodError):
    def __init__(self, detail: str, headers=None) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            headers=headers,
        )


class RequestValueError(SherwoodError):
    def __init__(self, detail: str, headers=None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            headers=headers,
        )


class InvalidDisplayNameError(SherwoodError):
    def __init__(self, reasons: list[str], headers=None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=" ".join(reasons),
            headers=headers,
        )


class InvalidPasswordError(SherwoodError):
    def __init__(self, reasons: list[str], headers=None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=" ".join(reasons),
            headers=headers,
        )


class IncorrectPasswordError(SherwoodError):
    def __init__(self, headers=None) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login credentials don't match our records.",
            headers=headers,
        )


class InvalidAccessToken(SherwoodError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid access token: {detail}",
            headers={"WWW-Authenticate": "Bearer"},
        )


class MissingUserError(SherwoodError):
    def __init__(
        self, user_id: str | None = None, email: str | None = None, headers=None
    ) -> None:
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
        display_name: str | None = None,
        headers=None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already exists"
            + ("" if user_id is None else f", user ID: {user_id}")
            + ("" if email is None else f", email: {email}")
            + ("" if display_name is None else f", display_name: {display_name}")
            + ".",
            headers=headers,
        )


class MissingPortfolioError(SherwoodError):
    def __init__(self, portfolio_id: str, headers=None) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio with ID {portfolio_id} missing.",
            headers=headers,
        )


class DuplicatePortfolioError(SherwoodError):
    def __init__(self, portfolio_id: str, headers=None) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Multiple portfolios with ID {portfolio_id}.",
            headers=headers,
        )


class InsufficientCashError(SherwoodError):
    def __init__(self, needed: float, actual: float, headers=None) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient cash, needed: {needed}, actual: {actual}.",
            headers=headers,
        )


class InsufficientHoldingsError(SherwoodError):
    def __init__(
        self,
        symbol: str | None = None,
        needed: float | None = None,
        actual: float | None = None,
        headers=None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient holdings."
            + ("" if symbol is None else f" Symbol: {symbol}.")
            + ("" if needed is None else f" Needed: {needed}.")
            + ("" if actual is None else f" Actual: {actual}."),
            headers=headers,
        )


class MarketDataProviderError(SherwoodError):
    def __init__(self, symbol: str, exceptions: list[Exception], headers=None) -> None:
        detail = f"Failed to get current price for symbol: {symbol}."
        for i, exc in enumerate(exceptions):
            detail += f" Error {i}: {exc}."
        super().__init__(
            status_code=status.HTTP_418_IM_A_TEAPOT,
            detail=detail,
            headers=headers,
        )

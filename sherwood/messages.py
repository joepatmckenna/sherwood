from enum import Enum
from pydantic import field_validator, model_validator, BaseModel, EmailStr
from sherwood.errors import (
    InvalidDisplayNameError,
    InvalidPasswordError,
    RequestValueError,
)
from sherwood.auth import validate_display_name, validate_password
from typing import Any


class _ModelWithEmail(BaseModel):
    email: EmailStr


class EmailValidatorMixin:
    @field_validator("email")
    def validate_email(cls, email):
        try:
            _ModelWithEmail(email=email)
            return email
        except ValueError as exc:
            raise RequestValueError(
                f"Invalid email: {email}. Error: {exc.errors()[0]['msg']}",
            ) from exc


class DisplayNameValidatorMixin:
    @field_validator("display_name")
    def validate_display_name_format(cls, password):
        reasons = validate_display_name(password)
        if reasons:
            raise InvalidDisplayNameError(reasons)
        return password


class PasswordValidatorMixin:
    @field_validator("password")
    def validate_password_format(cls, password):
        reasons = validate_password(password)
        if reasons:
            raise InvalidPasswordError(reasons)
        return password


class DollarsArePositiveValidatorMixin:
    @field_validator("dollars")
    def validate_dollars_are_positive(cls, dollars):
        if dollars <= 0:
            raise RequestValueError("Dollars must be positive.")
        return dollars


class SignUpRequest(
    BaseModel, EmailValidatorMixin, DisplayNameValidatorMixin, PasswordValidatorMixin
):
    email: str
    display_name: str
    password: str


class SignUpResponse(BaseModel):
    redirect_url: str


class SignInRequest(BaseModel, EmailValidatorMixin):
    email: str
    password: str


class SignInResponse(BaseModel):
    redirect_url: str


class BuyRequest(BaseModel, DollarsArePositiveValidatorMixin):
    symbol: str
    dollars: float


class BuyResponse(BaseModel):
    pass


class SellRequest(BaseModel, DollarsArePositiveValidatorMixin):
    symbol: str
    dollars: float


class SellResponse(BaseModel):
    pass


class InvestRequest(BaseModel, DollarsArePositiveValidatorMixin):
    investee_portfolio_id: int
    dollars: float


class InvestResponse(BaseModel):
    pass


class DivestRequest(BaseModel, DollarsArePositiveValidatorMixin):
    investee_portfolio_id: int
    dollars: float


class DivestResponse(BaseModel):
    pass


class LeaderboardRequest(BaseModel):
    class LeaderboardSortBy(Enum):
        LIFETIME_RETURN = "lifetime_return"
        AVERAGE_DAILY_RETURN = "average_daily_return"
        ASSETS_UNDER_MANAGEMENT = "assets_under_management"

    top_k: int
    sort_by: LeaderboardSortBy


class LeaderboardResponse(BaseModel):
    class LeaderboardRow(BaseModel):
        user_id: int
        user_display_name: str
        lifetime_return: float | None = None
        average_daily_return: float | None = None
        assets_under_management: float | None = None

    rows: list[LeaderboardRow]


class UserHoldingsRequest(BaseModel):
    user_id: int


class UserHoldingsResponse(BaseModel):
    class UserHoldingsRow(BaseModel):
        symbol: str
        units: float
        value: float
        lifetime_return: float
        lifetime_return_percent: float

    rows: list[UserHoldingsRow]


class PortfolioRequest(BaseModel):
    portfolio_id: int


class PortfolioResponse(BaseModel):
    portfolio: dict[str, Any]


__all__ = [
    "SignUpRequest",
    "SignUpResponse",
    "SignInRequest",
    "SignInResponse",
    "BuyRequest",
    "BuyResponse",
    "SellRequest",
    "SellResponse",
    "InvestRequest",
    "InvestResponse",
    "DivestRequest",
    "DivestResponse",
    "LeaderboardRequest",
    "LeaderboardResponse",
    "UserHoldingsRequest",
    "UserHoldingsResponse",
    "PortfolioRequest",
    "PortfolioResponse",
]

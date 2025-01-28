from datetime import datetime
from enum import Enum
from pydantic import field_validator, BaseModel, EmailStr
from sherwood.errors import (
    InvalidDisplayNameError,
    InvalidPasswordError,
    RequestValueError,
)
from sherwood.auth import validate_display_name, validate_password
from sherwood.models import TransactionType
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
    class Column(Enum):
        LIFETIME_RETURN = "lifetime_return"
        AVERAGE_DAILY_RETURN = "average_daily_return"
        ASSETS_UNDER_MANAGEMENT = "assets_under_management"

    columns: list[Column]
    sort_by: Column
    top_k: int


class LeaderboardResponse(BaseModel):
    class Row(BaseModel):
        user_id: int
        user_display_name: str
        portfolio_id: int
        columns: dict[str, Any]

    rows: list[Row]


class PortfolioHoldingsRequest(BaseModel):
    class Column(Enum):
        UNITS = "units"
        PRICE = "price"
        VALUE = "value"
        AVERAGE_DAILY_RETURN = "average_daily_return"
        LIFETIME_RETURN = "lifetime_return"

    portfolio_id: int
    columns: list[Column]
    sort_by: Column


class PortfolioHoldingsResponse(BaseModel):
    class Row(BaseModel):
        symbol: str
        columns: dict[str, Any]

    rows: list[Row]


class PortfolioHistoryRequest(BaseModel):
    class Column(Enum):
        DOLLARS = "dollars"
        PRICE = "price"

    portfolio_id: int
    columns: list[Column]


class PortfolioHistoryResponse(BaseModel):
    class Row(BaseModel):
        created: datetime
        type: TransactionType
        asset: str
        columns: dict[str, Any]

    rows: list[Row]


class PortfolioInvestorsRequest(BaseModel):
    class Column(Enum):
        AMOUNT_INVESTED = "amount_invested"
        VALUE = "value"
        AVERAGE_DAILY_RETURN = "average_daily_return"
        LIFETIME_RETURN = "lifetime_return"

    portfolio_id: int
    columns: list[Column]
    sort_by: Column


class PortfolioInvestorsResponse(BaseModel):
    class Row(BaseModel):
        user_id: int
        user_display_name: str
        columns: dict[str, Any]

    rows: list[Row]


class UserInvestmentsRequest(BaseModel):
    class Column(Enum):
        AMOUNT_INVESTED = "amount_invested"
        VALUE = "value"
        AVERAGE_DAILY_RETURN = "average_daily_return"
        LIFETIME_RETURN = "lifetime_return"

    user_id: int
    columns: list[Column]
    sort_by: Column


class UserInvestmentsResponse(BaseModel):
    class Row(BaseModel):
        user_id: int
        user_display_name: str
        columns: dict[str, Any]

    rows: list[Row]


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
    "PortfolioHoldingsRequest",
    "PortfolioHoldingsResponse",
    "PortfolioHistoryRequest",
    "PortfolioHistoryResponse",
    "PortfolioInvestorsRequest",
    "PortfolioInvestorsResponse",
    "UserInvestmentsRequest",
    "UserInvestmentsResponse",
]

from enum import Enum
from pydantic import field_validator, model_validator, BaseModel, EmailStr
from sherwood.errors import (
    InvalidDisplayNameError,
    InvalidPasswordError,
    RequestValueError,
)
from sherwood.auth import validate_display_name, validate_password
from typing import Any
from typing_extensions import Self


class OneOfMixin:
    def oneof(self):
        for k, v in self.model_dump().items():
            if v is not None:
                return getattr(self, k)

    @model_validator(mode="after")
    def validate_one_of(self) -> Self:
        if len([v for v in self.model_dump().values() if v is not None]) != 1:
            raise RequestValueError("More than one blob requested.")
        return self


class ModelWithEmail(BaseModel):
    email: EmailStr


class EmailValidatorMixin:
    @field_validator("email")
    def validate_email(cls, email):
        try:
            ModelWithEmail(email=email)
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


class LeaderboardSortBy(Enum):
    GAIN_OR_LOSS = "gain_or_loss"


class LeaderboardBlobRequest(BaseModel):
    top_k: int
    sort_by: LeaderboardSortBy


class LeaderboardBlobResponse(BaseModel):
    users: list[dict[str, Any]]


class BlobRequest(BaseModel, OneOfMixin):
    leaderboard: LeaderboardBlobRequest | None = None


class BlobResponse(BaseModel):
    key: str
    value: str


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
    "BlobRequest",
    "BlobResponse",
    "LeaderboardBlobRequest",
    "LeaderboardBlobResponse",
]

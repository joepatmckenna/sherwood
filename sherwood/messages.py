from pydantic import field_validator, BaseModel, EmailStr
from sherwood import errors
from sherwood.auth import validate_password
from sherwood.models import validate_display_name


class ModelWithEmail(BaseModel):
    email: EmailStr


class EmailValidatorMixin:
    @field_validator("email")
    def validate_email(cls, email):
        try:
            ModelWithEmail(email=email)
            return email
        except ValueError as exc:
            raise errors.RequestValueError(
                f"Invalid email: {email}. Error: {exc.errors()[0]['msg']}",
            ) from exc


class DisplayNameValidatorMixin:
    @field_validator("display_name")
    def validate_display_name_format(cls, password):
        reasons = validate_display_name(password)
        if reasons:
            raise errors.InvalidDisplayNameError(reasons)
        return password


class PasswordValidatorMixin:
    @field_validator("password")
    def validate_password_format(cls, password):
        reasons = validate_password(password)
        if reasons:
            raise errors.InvalidPasswordError(reasons)
        return password


class DollarsArePositiveValidatorMixin:
    @field_validator("dollars")
    def validate_dollars_are_positive(cls, dollars):
        if dollars <= 0:
            raise errors.RequestValueError("Dollars must be positive.")
        return dollars


class SignUpRequest(
    BaseModel, EmailValidatorMixin, DisplayNameValidatorMixin, PasswordValidatorMixin
):
    email: str
    display_name: str
    password: str


class SignInRequest(BaseModel, EmailValidatorMixin):
    email: str
    password: str


class BuyRequest(BaseModel, DollarsArePositiveValidatorMixin):
    symbol: str
    dollars: float


class SellRequest(BaseModel, DollarsArePositiveValidatorMixin):
    symbol: str
    dollars: float


class InvestRequest(BaseModel, DollarsArePositiveValidatorMixin):
    investee_portfolio_id: int
    dollars: float


class DivestRequest(BaseModel, DollarsArePositiveValidatorMixin):
    investee_portfolio_id: int
    dollars: float


class SignUpResponse(BaseModel):
    redirect_url: str


class SignInResponse(BaseModel):
    token_type: str
    access_token: str
    redirect_url: str


class BuyResponse(BaseModel):
    pass


class SellResponse(BaseModel):
    pass


class InvestResponse(BaseModel):
    pass


class DivestResponse(BaseModel):
    pass


__all__ = [
    "SignUpRequest",
    "SignInRequest",
    "BuyRequest",
    "SellRequest",
    "InvestRequest",
    "DivestRequest",
    "SignUpResponse",
    "SignInResponse",
    "BuyResponse",
    "SellResponse",
    "InvestResponse",
    "DivestResponse",
]

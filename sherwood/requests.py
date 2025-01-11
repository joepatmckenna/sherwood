from pydantic import field_validator, BaseModel, EmailStr
from sherwood import errors
from sherwood.auth import validate_password


class _ModelWithEmail(BaseModel):
    email: EmailStr


class EmailValidatorMixin:
    @field_validator("email")
    def validate_email(cls, email):
        try:
            _ModelWithEmail(email=email)
            return email
        except ValueError as exc:
            raise errors.RequestValueError(
                f"Invalid email: {email}. Error: {exc.errors()[0]['msg']}",
            ) from exc


class PasswordValidatorMixin:
    @field_validator("password")
    def validate_password_format(cls, password):
        is_valid, reasons = validate_password(password)
        if not is_valid:
            raise errors.InvalidPasswordError(reasons)
        return password


class DollarsArePositiveValidatorMixin:
    @field_validator("dollars")
    def validate_dollars_are_positive(cls, dollars):
        if dollars <= 0:
            raise errors.RequestValueError("Dollars must be positive.")
        return dollars


class SignUpRequest(BaseModel, EmailValidatorMixin, PasswordValidatorMixin):
    email: str
    password: str


class SignInRequest(BaseModel, EmailValidatorMixin):
    email: str
    password: str


class DepositRequest(BaseModel, DollarsArePositiveValidatorMixin):
    dollars: float


class WithdrawRequest(BaseModel, DollarsArePositiveValidatorMixin):
    dollars: float


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

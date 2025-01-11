from pydantic import BaseModel


class SignUpResponse(BaseModel):
    pass


class SignInResponse(BaseModel):
    token_type: str
    access_token: str


class DepositResponse(BaseModel):
    starting_balance: float
    ending_balance: float


class WithdrawResponse(BaseModel):
    starting_balance: float
    ending_balance: float


class BuyResponse(BaseModel):
    pass


class SellResponse(BaseModel):
    pass


class InvestResponse(BaseModel):
    pass


class DivestResponse(BaseModel):
    pass

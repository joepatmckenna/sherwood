from collections.abc import Iterable
from dataclasses import fields
import datetime
from enum import Enum
import re
from sherwood import errors
from sherwood.auth import password_context, validate_password
from six import string_types
from sqlalchemy import func, ForeignKey, Index
from sqlalchemy.event import listens_for
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
    Session,
)
from typing import Any

_MIN_DISPLAY_NAME_LENGTH = 3
_MAX_DISPLAY_NAME_LENGTH = 32

get_current_time = lambda: datetime.datetime.now(datetime.timezone.utc)


class BaseModel(DeclarativeBase, MappedAsDataclass):
    __abstract__ = True

    created_at: Mapped[datetime.datetime] = mapped_column(
        init=False,
        repr=False,
        default_factory=get_current_time,
        nullable=False,
        compare=False,
    )

    last_updated_at: Mapped[datetime.datetime] = mapped_column(
        init=False,
        repr=False,
        default_factory=get_current_time,
        nullable=False,
        onupdate=get_current_time,
        compare=False,
    )


class User(BaseModel):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        init=False,
        primary_key=True,
        autoincrement=True,
        compare=True,
        repr=True,
    )

    email: Mapped[str] = mapped_column(
        nullable=False,
        index=True,
        unique=True,
        compare=True,
        repr=True,
    )

    display_name: Mapped[str] = mapped_column(
        nullable=False,
        index=True,
        unique=False,
        compare=True,
        repr=True,
    )

    password: Mapped[str] = mapped_column(
        repr=False,
        nullable=False,
        compare=False,
    )

    is_verified: Mapped[bool] = mapped_column(
        nullable=False,
        init=False,
        repr=True,
        default=False,
    )

    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
        init=False,
        repr=True,
        compare=True,
    )

    __table_args__ = (
        Index(
            "ix_users_display_name_lower",
            func.lower(display_name),
            unique=True,
        ),
    )


class Portfolio(BaseModel):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        init=False,
        primary_key=True,
        compare=True,
        repr=True,
    )

    cash: Mapped[float] = mapped_column(
        default=0,
        compare=True,
        repr=True,
    )

    holdings: Mapped[list["Holding"]] = relationship(
        "Holding",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        default_factory=list,
        compare=True,
        repr=True,
    )

    ownership: Mapped[list["Ownership"]] = relationship(
        "Ownership",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        default_factory=list,
        compare=True,
        repr=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        uselist=False,
        back_populates="portfolio",
        init=False,
        repr=False,
        compare=False,
    )


class Holding(BaseModel):
    __tablename__ = "holdings"

    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        primary_key=True,
        compare=True,
        repr=True,
    )

    symbol: Mapped[str] = mapped_column(
        primary_key=True,
        compare=True,
        repr=True,
    )

    cost: Mapped[float] = mapped_column(
        compare=True,
        repr=True,
    )

    units: Mapped[float] = mapped_column(
        compare=True,
        repr=True,
    )

    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="holdings",
        init=False,
        repr=False,
        compare=False,
    )


class Ownership(BaseModel):
    __tablename__ = "ownership"

    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        primary_key=True,
        compare=True,
        repr=True,
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        compare=True,
        repr=True,
    )

    cost: Mapped[float] = mapped_column(
        compare=True,
        repr=True,
    )

    percent: Mapped[float] = mapped_column(
        compare=True,
        repr=True,
    )

    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="ownership",
        init=False,
        repr=False,
        compare=False,
    )


class ReasonDisplayNameInvalid(Enum):
    TOO_SHORT = (
        f"Display name must be at least {_MIN_DISPLAY_NAME_LENGTH} characters long."
    )
    TOO_Long = (
        f"Display name must not be longer than {_MAX_DISPLAY_NAME_LENGTH} characters."
    )
    CONTAINS_SPECIAL = "Display name must only use letters (a-z or A-Z), numbers (0-9), underscores (_), hyphens (-), or periods (.)."
    STARTS_WITH_SPECIAL = "Display name must begin with a letter (a-z or A-Z)."


def validate_display_name(display_name: str) -> list[str]:
    reasons = []
    if len(display_name) < _MIN_DISPLAY_NAME_LENGTH:
        reasons.append(ReasonDisplayNameInvalid.TOO_SHORT.value)
    if len(display_name) > _MAX_DISPLAY_NAME_LENGTH:
        reasons.append(ReasonDisplayNameInvalid.TOO_LONG.value)
    if not re.match(r"^[a-zA-Z0-9._\-]+$", display_name):
        reasons.append(ReasonDisplayNameInvalid.CONTAINS_SPECIAL.value)
    if not re.match(r"^[a-zA-Z]", display_name):
        reasons.append(ReasonDisplayNameInvalid.STARTS_WITH_SPECIAL.value)
    return reasons


@listens_for(User, "before_insert")
def validate_user(mapper, connection, target):
    reasons = validate_display_name(target.display_name)
    if reasons:
        raise errors.InvalidDisplayNameError(target.display_name)
    reasons = validate_password(target.password)
    if reasons:
        raise errors.InvalidPasswordError(reasons)
    target.password = password_context.hash(target.password)


def create_user(
    db: Session, email: str, display_name: str, password: str, cash: float = 0
) -> User:
    user = User(email=email, display_name=display_name, password=password)
    user.portfolio = Portfolio(cash=cash)
    db.add(user)
    try:
        db.commit()
        return user
    except Exception as exc:
        db.rollback()
        raise errors.InternalServerError(detail="Failed to create user.") from exc


def to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, Iterable) and not isinstance(obj, string_types):
        obj = [to_dict(x) for x in obj]
    if isinstance(obj, (User, Portfolio, Holding, Ownership)):
        obj = {
            field.name: to_dict(getattr(obj, field.name))
            for field in fields(obj)
            if field.repr
        }
    return obj

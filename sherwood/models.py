from dataclasses import fields
import datetime
from sherwood import errors, utils
from sherwood.auth import password_context, validate_password
from sqlalchemy import ForeignKey
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


class BaseModel(DeclarativeBase, MappedAsDataclass):
    __abstract__ = True

    created_at: Mapped[datetime.datetime] = mapped_column(
        init=False,
        repr=False,
        default_factory=utils.get_current_time,
        nullable=False,
        compare=False,
    )

    last_updated_at: Mapped[datetime.datetime] = mapped_column(
        init=False,
        repr=False,
        default_factory=utils.get_current_time,
        nullable=False,
        onupdate=utils.get_current_time,
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
        init=False,
        repr=True,
        nullable=True,
        unique=True,
        compare=True,
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


class Portfolio(BaseModel):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
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
        ForeignKey("portfolios.id"),
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
        ForeignKey("portfolios.id"),
        primary_key=True,
        compare=True,
        repr=True,
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
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


@listens_for(User, "before_insert")
def parse_password(mapper, connection, target):
    password_is_valid, message = validate_password(target.password)
    if not password_is_valid:
        raise errors.InvalidPasswordError(message)
    target.password = password_context.hash(target.password)


def create_user(db: Session, email: str, password: str) -> User:
    with db.begin_nested():
        user = User(email, password)
        user.portfolio = Portfolio()
        db.add(user)
        return user


def to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, (User, Portfolio, Holding, Ownership)):
        obj = {
            field.name: to_dict(getattr(obj, field.name))
            for field in fields(obj)
            if field.repr
        }
    return obj

import datetime
import logging
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
    )

    email: Mapped[str] = mapped_column(
        nullable=False,
        index=True,
        unique=True,
        compare=True,
    )

    password: Mapped[str] = mapped_column(
        repr=False,
        nullable=False,
        compare=False,
    )

    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
        init=False,
        repr=False,
        compare=True,
    )


class Portfolio(BaseModel):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        init=False,
        primary_key=True,
        compare=True,
    )

    cash: Mapped[float] = mapped_column(
        default=0,
        compare=True,
    )

    holdings: Mapped[list["Holding"]] = relationship(
        "Holding",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        default_factory=list,
        compare=True,
    )

    ownership: Mapped[list["Ownership"]] = relationship(
        "Ownership",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        default_factory=list,
        compare=True,
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
    )

    symbol: Mapped[str] = mapped_column(
        primary_key=True,
        compare=True,
    )

    cost: Mapped[float] = mapped_column(
        compare=True,
    )

    units: Mapped[float] = mapped_column(
        compare=True,
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
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        primary_key=True,
        compare=True,
    )

    cost: Mapped[float] = mapped_column(
        compare=True,
    )

    percent: Mapped[float] = mapped_column(
        compare=True,
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


def _maybe_commit(db):
    try:
        db.commit()
    except Exception as exc:
        logging.error("Error creating user: %s", exc)
        db.rollback()
        raise


def create_user(db: Session, email: str, password: str) -> User:
    user = User(email, password)
    user.portfolio = Portfolio()
    db.add(user)
    _maybe_commit(db)
    user.portfolio.ownership.append(Ownership(user.id, user.id, 0, 1))
    _maybe_commit(db)
    return user


def to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, User):
        return {
            "id": obj.id,
            "email": obj.email,
            "portfolio": to_dict(obj.portfolio),
        }
    if isinstance(obj, Portfolio):
        return {
            "id": obj.id,
            "cash": obj.cash,
            "holdings": [to_dict(h) for h in obj.holdings],
            "ownership": [to_dict(o) for o in obj.ownership],
        }
    if isinstance(obj, Holding):
        return {
            "portfolio_id": obj.portfolio_id,
            "symbol": obj.symbol,
            "cost": obj.cost,
            "units": obj.units,
        }
    if isinstance(obj, Ownership):
        return {
            "portfolio_id": obj.portfolio_id,
            "owner_id": obj.owner_id,
            "cost": obj.cost,
            "percent": obj.percent,
        }
    return obj

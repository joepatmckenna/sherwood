from collections.abc import Iterable
from dataclasses import fields
from datetime import datetime
from sherwood.db import maybe_commit
from sherwood.errors import DuplicateQuoteError
from six import string_types
from sqlalchemy import func, ForeignKey, Index
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
    Session,
)
from sqlalchemy.orm.attributes import flag_modified
from typing import Any


class BaseModel(DeclarativeBase, MappedAsDataclass):
    __abstract__ = True

    created: Mapped[datetime] = mapped_column(
        init=False,
        repr=True,
        default_factory=datetime.now,
        nullable=False,
        compare=False,
    )

    last_modified: Mapped[datetime] = mapped_column(
        init=False,
        repr=True,
        default_factory=datetime.now,
        compare=False,
        nullable=False,
        onupdate=datetime.now,
    )


class User(BaseModel):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        init=False,
        repr=True,
        primary_key=True,
        autoincrement=True,
        compare=True,
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
        primary_key=True,
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


class Quote(BaseModel):
    __tablename__ = "quotes"

    symbol: Mapped[str] = mapped_column(
        primary_key=True,
        init=True,
        repr=True,
        compare=True,
        nullable=False,
        unique=True,
    )

    price: Mapped[float] = mapped_column(
        init=True,
        repr=True,
        compare=True,
        nullable=False,
    )


class Blob(BaseModel):
    __tablename__ = "blobs"

    key: Mapped[str] = mapped_column(
        init=True,
        primary_key=True,
        compare=True,
        repr=True,
        unique=False,
        nullable=False,
    )

    value: Mapped[str] = mapped_column(
        init=True,
        compare=True,
        repr=True,
        unique=False,
        nullable=False,
    )


def create_user(
    db: Session,
    email: str,
    display_name: str,
    password: str,
    starting_balance: float = 0,
) -> User:
    user = User(email=email, display_name=display_name, password=password)
    db.add(user)
    maybe_commit(db, "Failed to create user.")
    portfolio_id = user.id
    user.portfolio = Portfolio(
        id=portfolio_id,
        holdings=[
            Holding(
                portfolio_id=portfolio_id,
                symbol="USD",
                cost=starting_balance,
                units=starting_balance,
            ),
        ],
        ownership=[
            Ownership(
                portfolio_id=portfolio_id,
                owner_id=user.id,
                cost=starting_balance,
                percent=1,
            )
        ],
    )
    maybe_commit(db, "Failed to create portfolio for new user.")
    db.refresh(user)
    return user


def create_quote(db: Session, symbol: str, price: float) -> Quote:
    quote = Quote(symbol=symbol, price=price)
    db.add(quote)
    maybe_commit(db, "Failed to create quote.")
    return quote


def update_quote(db: Session, quote: Quote, price: float) -> Quote:
    quote.price = price
    flag_modified(quote, "price")
    maybe_commit(db, "Failed to update quote.")
    return quote


def upsert_quote(db: Session, symbol: str, price: float) -> Quote:
    try:
        quote = db.query(Quote).filter_by(symbol=symbol).with_for_update().one_or_none()
    except MultipleResultsFound:
        raise DuplicateQuoteError(symbol=symbol)
    if quote is None:
        return create_quote(db, symbol, price)
    else:
        return update_quote(db, quote, price)


def create_blob(db: Session, key: str, value: str) -> Blob:
    blob = Blob(key=key, value=value)
    db.add(blob)
    maybe_commit(db, "Failed to create blob.")
    return blob


def update_blob(db: Session, blob: Blob, value: str) -> Blob:
    blob.value = value
    flag_modified(blob, "value")
    maybe_commit(db, "Failed to update blob.")
    return blob


def upsert_blob(db: Session, key: str, value: str) -> Blob:
    blob = db.query(Blob).filter_by(key=key).with_for_update().one_or_none()
    if blob is None:
        return create_blob(db, key, value)
    else:
        return update_blob(db, blob, value)


def to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, Iterable) and not isinstance(obj, string_types):
        obj = [to_dict(x) for x in obj]
    if isinstance(obj, BaseModel):
        obj = {
            field.name: to_dict(getattr(obj, field.name))
            for field in fields(obj)
            if field.repr
        }
    return obj


def has_expired(model: BaseModel, seconds: int):
    return (datetime.now() - model.last_modified).total_seconds() > seconds

from sqlalchemy.orm import Session
from sherwood.db import maybe_commit
from sherwood.errors import MarketDataProviderError
from sherwood.models import has_expired, Quote
from sqlalchemy.orm.attributes import flag_modified
import yfinance

_PRICE_DELAY_SECONDS = 300


def _fetch_prices(symbols) -> dict[str, float]:
    try:
        tickers = yfinance.Tickers(symbols)
        return {
            symbol: tickers.tickers[symbol].info["currentPrice"] for symbol in symbols
        }
    except Exception as exc:
        raise MarketDataProviderError(
            f"Failed to get prices, symbols: {', '.join(symbols)}. Error: {exc}"
        ) from exc


def get_prices(db: Session, symbols: list[str]) -> dict[str, float]:
    symbols_by_status = {"current": set(), "expired": set(), "missing": set(symbols)}
    price_by_symbol = {}

    quotes_to_update = []

    for quote in db.query(Quote).filter(Quote.symbol.in_(symbols)).all():
        symbols_by_status["missing"].remove(quote.symbol)
        if has_expired(quote, _PRICE_DELAY_SECONDS):
            symbols_by_status["expired"].add(quote.symbol)
            quotes_to_update.append(quote)
        else:
            symbols_by_status["current"].add(quote.symbol)
            price_by_symbol[quote.symbol] = quote.price

    if s := set.union(symbols_by_status["expired"], symbols_by_status["missing"]):
        price_by_symbol.update(_fetch_prices(list(s)))
        for symbol in symbols_by_status["missing"]:
            db.add(Quote(symbol=symbol, price=price_by_symbol[symbol]))
        for quote in quotes_to_update:
            quote.price = price_by_symbol[quote.symbol]
            flag_modified(quote, "price")
            db.add(quote)
        maybe_commit(db, "Failed to upsert quotes.")

    return price_by_symbol


def get_price(db: Session, symbol: str) -> float:
    return get_prices(db, [symbol])[symbol]

from dataclasses import dataclass
from sherwood import errors
import time
import yfinance as yf


@dataclass
class Quote:
    symbol: str
    time: float
    price: float


class MarketDataProvider:
    def __init__(self, latency=10):
        self._by_symbol = {}
        self._latency = latency

    def get_price(self, symbol: str) -> float:
        quote = self._by_symbol.get(symbol)
        if quote is not None and time.time() - quote.time < self._latency:
            return quote.price
        attempts = 5
        exceptions = []
        while attempts:
            try:
                price = yf.Ticker(symbol).info["currentPrice"]
                self._by_symbol[symbol] = Quote(symbol, time.time(), price)
                return price
            except Exception as exc:
                exceptions.append(exc)
                attempts -= 1
                time.sleep(0.02)
        raise errors.MarketDataProviderError(symbol, exceptions)

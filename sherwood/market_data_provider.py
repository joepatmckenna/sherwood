from dataclasses import dataclass
import time
import yfinance as yf


@dataclass
class Quote:
    symbol: str
    time: float
    price: float


class MarketDataProvider:
    def __init__(self, latency=60):
        self._by_symbol = {}
        self._latency = latency

    def get_price(self, symbol: str) -> float:
        quote = self._by_symbol.get(symbol)
        if quote is not None and time.time() - quote.time < self._latency:
            return quote.price
        attempts = 5
        while attempts:
            try:
                price = yf.Ticker(symbol).info["currentPrice"]
                self._by_symbol[symbol] = Quote(symbol, time.time(), price)
                return price
            except:
                attempts -= 1
                time.sleep(0.02)
        raise Exception("failed to get price")

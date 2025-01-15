from dataclasses import dataclass
import logging
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

    def prefetch_prices(self, symbols: list[str], attempts=5):
        exceptions = []
        while attempts:
            try:
                ticker_data = yf.Tickers(" ".join(symbols))
                for symbol in symbols:
                    if (
                        symbol not in ticker_data.tickers
                        or "currentPrice" not in ticker_data.tickers[symbol].info
                    ):
                        logging.error(f"Missing price for symbol {symbol}")
                        continue
                    self._by_symbol[symbol] = Quote(
                        symbol=symbol,
                        time=time.time(),
                        price=ticker_data.tickers[symbol].info["currentPrice"],
                    )
            except Exception as exc:
                exceptions.append(exc)
                attempts -= 1
                time.sleep(0.02)
        raise errors.MarketDataProviderError(", ".join(symbols), exceptions)

        # for symbol in symbols:
        #     try:
        #         self._by_symbol[symbol] = Quote(
        #             symbol=symbol,
        #             time=time.time(),
        #             price=yf.Ticker(symbol).info["currentPrice"],
        #         )
        #     except Exception as exc:
        #         print(f"Failed to prefetch {symbol}: {exc}")

    def get_price(self, symbol: str, attempts: int = 5) -> float:
        quote = self._by_symbol.get(symbol)
        if quote is not None and time.time() - quote.time < self._latency:
            return quote.price
        exceptions = []
        while attempts:
            try:
                self._by_symbol[symbol] = Quote(
                    symbol=symbol,
                    time=time.time(),
                    price=yf.Ticker(symbol).info["currentPrice"],
                )
                return self._by_symbol[symbol].price
            except Exception as exc:
                exceptions.append(exc)
                attempts -= 1
                time.sleep(0.02)
        raise errors.MarketDataProviderError(symbol, exceptions)

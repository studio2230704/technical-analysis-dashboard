"""Watchlist management with individual alert settings."""

import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class StockAlert:
    """Alert settings for a single stock."""

    ticker: str
    name: str = ""
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    cross_enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "StockAlert":
        return cls(
            ticker=data.get("ticker", ""),
            name=data.get("name", ""),
            rsi_oversold=data.get("rsi_oversold", 30),
            rsi_overbought=data.get("rsi_overbought", 70),
            cross_enabled=data.get("cross_enabled", True),
        )


class WatchlistManager:
    """Manage watchlist with persistent storage."""

    def __init__(self, filepath: str | Path = "watchlist.json"):
        self.filepath = Path(filepath)
        self._stocks: dict[str, StockAlert] = {}
        self.load()

    def load(self) -> None:
        """Load watchlist from JSON file."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._stocks = {
                        item["ticker"]: StockAlert.from_dict(item)
                        for item in data.get("stocks", [])
                    }
            except (json.JSONDecodeError, KeyError):
                self._stocks = {}
        else:
            self._stocks = {}

    def save(self) -> None:
        """Save watchlist to JSON file."""
        data = {
            "stocks": [stock.to_dict() for stock in self._stocks.values()]
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, stock: StockAlert) -> None:
        """Add or update a stock."""
        self._stocks[stock.ticker.upper()] = stock
        self.save()

    def remove(self, ticker: str) -> bool:
        """Remove a stock by ticker."""
        ticker = ticker.upper()
        if ticker in self._stocks:
            del self._stocks[ticker]
            self.save()
            return True
        return False

    def get(self, ticker: str) -> StockAlert | None:
        """Get a stock by ticker."""
        return self._stocks.get(ticker.upper())

    def update(self, ticker: str, **kwargs) -> bool:
        """Update stock settings."""
        ticker = ticker.upper()
        if ticker in self._stocks:
            stock = self._stocks[ticker]
            for key, value in kwargs.items():
                if hasattr(stock, key):
                    setattr(stock, key, value)
            self.save()
            return True
        return False

    def list_all(self) -> list[StockAlert]:
        """Get all stocks in watchlist."""
        return list(self._stocks.values())

    def get_tickers(self) -> list[str]:
        """Get all ticker symbols."""
        return list(self._stocks.keys())

    def __len__(self) -> int:
        return len(self._stocks)

    def __contains__(self, ticker: str) -> bool:
        return ticker.upper() in self._stocks

"""Data fetching with yfinance."""

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


def fetch_stock_data(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch stock data from Yahoo Finance.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', '7203.T')
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

    Returns:
        DataFrame with OHLCV data
    """
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)

    if df.empty:
        raise ValueError(f"No data found for ticker: {ticker}")

    return df


def get_stock_info(ticker: str) -> dict:
    """Get stock information.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with stock info
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    return {
        "name": info.get("longName", info.get("shortName", ticker)),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "currency": info.get("currency", "USD"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "dividend_yield": info.get("dividendYield"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
    }


def get_current_price(ticker: str) -> dict:
    """Get current price information.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with current price data
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    return {
        "price": info.get("currentPrice", info.get("regularMarketPrice")),
        "change": info.get("regularMarketChange"),
        "change_percent": info.get("regularMarketChangePercent"),
        "volume": info.get("regularMarketVolume"),
        "prev_close": info.get("regularMarketPreviousClose"),
    }

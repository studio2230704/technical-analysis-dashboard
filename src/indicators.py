"""Technical indicators calculation."""

import pandas as pd
import numpy as np


def calculate_sma(data: pd.Series, window: int) -> pd.Series:
    """Calculate Simple Moving Average.

    Args:
        data: Price series (typically Close)
        window: Window size in days

    Returns:
        SMA series
    """
    return data.rolling(window=window).mean()


def calculate_ema(data: pd.Series, window: int) -> pd.Series:
    """Calculate Exponential Moving Average.

    Args:
        data: Price series
        window: Window size in days

    Returns:
        EMA series
    """
    return data.ewm(span=window, adjust=False).mean()


def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    """Calculate Relative Strength Index.

    Args:
        data: Price series (typically Close)
        window: RSI period (default: 14)

    Returns:
        RSI series (0-100)
    """
    delta = data.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(
    data: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, pd.Series]:
    """Calculate MACD (Moving Average Convergence Divergence).

    Args:
        data: Price series
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)

    Returns:
        Dictionary with 'macd', 'signal', 'histogram'
    """
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)

    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line

    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    }


def calculate_bollinger_bands(
    data: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> dict[str, pd.Series]:
    """Calculate Bollinger Bands.

    Args:
        data: Price series
        window: Moving average period (default: 20)
        num_std: Number of standard deviations (default: 2)

    Returns:
        Dictionary with 'middle', 'upper', 'lower', 'bandwidth'
    """
    middle = calculate_sma(data, window)
    std = data.rolling(window=window).std()

    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    bandwidth = (upper - lower) / middle * 100

    return {
        "middle": middle,
        "upper": upper,
        "lower": lower,
        "bandwidth": bandwidth,
    }


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to DataFrame.

    Args:
        df: DataFrame with OHLCV data

    Returns:
        DataFrame with indicators added
    """
    result = df.copy()
    close = result["Close"]

    # Moving Averages
    result["SMA_5"] = calculate_sma(close, 5)
    result["SMA_25"] = calculate_sma(close, 25)
    result["SMA_75"] = calculate_sma(close, 75)
    result["SMA_200"] = calculate_sma(close, 200)

    # RSI
    result["RSI"] = calculate_rsi(close, 14)

    # MACD
    macd = calculate_macd(close)
    result["MACD"] = macd["macd"]
    result["MACD_Signal"] = macd["signal"]
    result["MACD_Histogram"] = macd["histogram"]

    # Bollinger Bands
    bb = calculate_bollinger_bands(close)
    result["BB_Middle"] = bb["middle"]
    result["BB_Upper"] = bb["upper"]
    result["BB_Lower"] = bb["lower"]
    result["BB_Bandwidth"] = bb["bandwidth"]

    return result

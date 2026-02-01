"""Signal detection for technical analysis."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

import pandas as pd


class SignalType(Enum):
    """Signal type enumeration."""

    GOLDEN_CROSS = "golden_cross"
    DEAD_CROSS = "dead_cross"
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    MACD_BULLISH = "macd_bullish"
    MACD_BEARISH = "macd_bearish"
    BB_LOWER_TOUCH = "bb_lower_touch"
    BB_UPPER_TOUCH = "bb_upper_touch"


@dataclass
class Signal:
    """Trading signal."""

    signal_type: SignalType
    date: date
    price: float
    description: str
    is_bullish: bool


def detect_ma_crossovers(
    df: pd.DataFrame,
    short_ma: str = "SMA_25",
    long_ma: str = "SMA_75",
) -> list[Signal]:
    """Detect Golden Cross and Dead Cross signals.

    Args:
        df: DataFrame with MA columns
        short_ma: Short-term MA column name
        long_ma: Long-term MA column name

    Returns:
        List of crossover signals
    """
    signals = []

    if short_ma not in df.columns or long_ma not in df.columns:
        return signals

    # Calculate crossover
    df_copy = df.copy()
    df_copy["short_above"] = df_copy[short_ma] > df_copy[long_ma]
    df_copy["crossover"] = df_copy["short_above"].diff()

    for idx, row in df_copy.iterrows():
        if pd.isna(row["crossover"]):
            continue

        if row["crossover"] == True:  # Golden Cross
            signals.append(
                Signal(
                    signal_type=SignalType.GOLDEN_CROSS,
                    date=idx.date() if hasattr(idx, "date") else idx,
                    price=row["Close"],
                    description=f"ゴールデンクロス: {short_ma}が{long_ma}を上抜け",
                    is_bullish=True,
                )
            )
        elif row["crossover"] == False:  # Dead Cross
            signals.append(
                Signal(
                    signal_type=SignalType.DEAD_CROSS,
                    date=idx.date() if hasattr(idx, "date") else idx,
                    price=row["Close"],
                    description=f"デッドクロス: {short_ma}が{long_ma}を下抜け",
                    is_bullish=False,
                )
            )

    return signals


def detect_rsi_signals(
    df: pd.DataFrame,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> list[Signal]:
    """Detect RSI oversold/overbought signals.

    Args:
        df: DataFrame with RSI column
        oversold: Oversold threshold (default: 30)
        overbought: Overbought threshold (default: 70)

    Returns:
        List of RSI signals
    """
    signals = []

    if "RSI" not in df.columns:
        return signals

    df_copy = df.copy()
    df_copy["prev_rsi"] = df_copy["RSI"].shift(1)

    for idx, row in df_copy.iterrows():
        if pd.isna(row["RSI"]) or pd.isna(row["prev_rsi"]):
            continue

        # Oversold -> Recovery
        if row["prev_rsi"] < oversold and row["RSI"] >= oversold:
            signals.append(
                Signal(
                    signal_type=SignalType.RSI_OVERSOLD,
                    date=idx.date() if hasattr(idx, "date") else idx,
                    price=row["Close"],
                    description=f"RSI売られすぎ解消: {row['RSI']:.1f}",
                    is_bullish=True,
                )
            )

        # Overbought -> Decline
        if row["prev_rsi"] > overbought and row["RSI"] <= overbought:
            signals.append(
                Signal(
                    signal_type=SignalType.RSI_OVERBOUGHT,
                    date=idx.date() if hasattr(idx, "date") else idx,
                    price=row["Close"],
                    description=f"RSI買われすぎ解消: {row['RSI']:.1f}",
                    is_bullish=False,
                )
            )

    return signals


def detect_macd_signals(df: pd.DataFrame) -> list[Signal]:
    """Detect MACD crossover signals.

    Args:
        df: DataFrame with MACD columns

    Returns:
        List of MACD signals
    """
    signals = []

    if "MACD" not in df.columns or "MACD_Signal" not in df.columns:
        return signals

    df_copy = df.copy()
    df_copy["macd_above"] = df_copy["MACD"] > df_copy["MACD_Signal"]
    df_copy["macd_cross"] = df_copy["macd_above"].diff()

    for idx, row in df_copy.iterrows():
        if pd.isna(row["macd_cross"]):
            continue

        if row["macd_cross"] == True:  # Bullish
            signals.append(
                Signal(
                    signal_type=SignalType.MACD_BULLISH,
                    date=idx.date() if hasattr(idx, "date") else idx,
                    price=row["Close"],
                    description="MACDがシグナル線を上抜け（買いシグナル）",
                    is_bullish=True,
                )
            )
        elif row["macd_cross"] == False:  # Bearish
            signals.append(
                Signal(
                    signal_type=SignalType.MACD_BEARISH,
                    date=idx.date() if hasattr(idx, "date") else idx,
                    price=row["Close"],
                    description="MACDがシグナル線を下抜け（売りシグナル）",
                    is_bullish=False,
                )
            )

    return signals


def detect_bollinger_signals(df: pd.DataFrame) -> list[Signal]:
    """Detect Bollinger Band touch signals.

    Args:
        df: DataFrame with Bollinger Band columns

    Returns:
        List of BB signals
    """
    signals = []

    required = ["Close", "BB_Lower", "BB_Upper"]
    if not all(col in df.columns for col in required):
        return signals

    for idx, row in df.iterrows():
        if pd.isna(row["BB_Lower"]) or pd.isna(row["BB_Upper"]):
            continue

        if row["Close"] <= row["BB_Lower"]:
            signals.append(
                Signal(
                    signal_type=SignalType.BB_LOWER_TOUCH,
                    date=idx.date() if hasattr(idx, "date") else idx,
                    price=row["Close"],
                    description="ボリンジャーバンド下限タッチ",
                    is_bullish=True,
                )
            )
        elif row["Close"] >= row["BB_Upper"]:
            signals.append(
                Signal(
                    signal_type=SignalType.BB_UPPER_TOUCH,
                    date=idx.date() if hasattr(idx, "date") else idx,
                    price=row["Close"],
                    description="ボリンジャーバンド上限タッチ",
                    is_bullish=False,
                )
            )

    return signals


def detect_all_signals(df: pd.DataFrame, lookback_days: int = 30) -> list[Signal]:
    """Detect all signals within lookback period.

    Args:
        df: DataFrame with all indicators
        lookback_days: Number of days to look back

    Returns:
        List of all signals, sorted by date descending
    """
    # Filter to lookback period
    recent_df = df.tail(lookback_days)

    all_signals = []

    # MA Crossovers (25/75)
    all_signals.extend(detect_ma_crossovers(recent_df, "SMA_25", "SMA_75"))

    # MA Crossovers (5/25)
    all_signals.extend(detect_ma_crossovers(recent_df, "SMA_5", "SMA_25"))

    # RSI
    all_signals.extend(detect_rsi_signals(recent_df))

    # MACD
    all_signals.extend(detect_macd_signals(recent_df))

    # Bollinger Bands
    all_signals.extend(detect_bollinger_signals(recent_df))

    # Sort by date descending
    all_signals.sort(key=lambda s: s.date, reverse=True)

    return all_signals

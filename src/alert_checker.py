"""Alert checker for stock watchlist."""

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from data import fetch_stock_data
from indicators import add_all_indicators
from notifier import (
    format_golden_cross_alert,
    format_rsi_alert,
    format_dead_cross_alert,
    send_line_notification,
)


@dataclass
class Alert:
    """Represents a triggered alert."""

    ticker: str
    alert_type: str
    message: str
    timestamp: datetime


def load_watchlist(csv_path: str | Path) -> list[str]:
    """Load watchlist from CSV file.

    Args:
        csv_path: Path to watchlist CSV file

    Returns:
        List of ticker symbols
    """
    tickers = []
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Watchlist file not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get("ticker", "").strip().upper()
            if ticker:
                tickers.append(ticker)

    return tickers


def check_golden_cross(df: pd.DataFrame, ticker: str) -> Alert | None:
    """Check for golden cross signal.

    Golden cross: SMA_25 crosses above SMA_75

    Args:
        df: DataFrame with indicators
        ticker: Stock ticker symbol

    Returns:
        Alert if golden cross detected, None otherwise
    """
    if len(df) < 2:
        return None

    if "SMA_25" not in df.columns or "SMA_75" not in df.columns:
        return None

    current = df.iloc[-1]
    previous = df.iloc[-2]

    # Check if SMA_25 crossed above SMA_75 today
    if (
        pd.notna(current["SMA_25"]) and
        pd.notna(current["SMA_75"]) and
        pd.notna(previous["SMA_25"]) and
        pd.notna(previous["SMA_75"])
    ):
        cross_today = current["SMA_25"] > current["SMA_75"]
        cross_yesterday = previous["SMA_25"] <= previous["SMA_75"]

        if cross_today and cross_yesterday:
            date_str = current.name.strftime("%Y-%m-%d")
            message = format_golden_cross_alert(
                ticker=ticker,
                price=current["Close"],
                date=date_str
            )
            return Alert(
                ticker=ticker,
                alert_type="golden_cross",
                message=message,
                timestamp=datetime.now()
            )

    return None


def check_dead_cross(df: pd.DataFrame, ticker: str) -> Alert | None:
    """Check for dead cross signal.

    Dead cross: SMA_25 crosses below SMA_75

    Args:
        df: DataFrame with indicators
        ticker: Stock ticker symbol

    Returns:
        Alert if dead cross detected, None otherwise
    """
    if len(df) < 2:
        return None

    if "SMA_25" not in df.columns or "SMA_75" not in df.columns:
        return None

    current = df.iloc[-1]
    previous = df.iloc[-2]

    if (
        pd.notna(current["SMA_25"]) and
        pd.notna(current["SMA_75"]) and
        pd.notna(previous["SMA_25"]) and
        pd.notna(previous["SMA_75"])
    ):
        cross_today = current["SMA_25"] < current["SMA_75"]
        cross_yesterday = previous["SMA_25"] >= previous["SMA_75"]

        if cross_today and cross_yesterday:
            date_str = current.name.strftime("%Y-%m-%d")
            message = format_dead_cross_alert(
                ticker=ticker,
                price=current["Close"],
                date=date_str
            )
            return Alert(
                ticker=ticker,
                alert_type="dead_cross",
                message=message,
                timestamp=datetime.now()
            )

    return None


def check_rsi_oversold(df: pd.DataFrame, ticker: str, threshold: float = 30) -> Alert | None:
    """Check for RSI oversold condition.

    Args:
        df: DataFrame with indicators
        ticker: Stock ticker symbol
        threshold: RSI threshold for oversold (default: 30)

    Returns:
        Alert if RSI is oversold, None otherwise
    """
    if "RSI" not in df.columns:
        return None

    current = df.iloc[-1]
    rsi = current.get("RSI")

    if pd.notna(rsi) and rsi < threshold:
        message = format_rsi_alert(
            ticker=ticker,
            price=current["Close"],
            rsi=rsi,
            signal_type="oversold"
        )
        return Alert(
            ticker=ticker,
            alert_type="rsi_oversold",
            message=message,
            timestamp=datetime.now()
        )

    return None


def check_rsi_overbought(df: pd.DataFrame, ticker: str, threshold: float = 70) -> Alert | None:
    """Check for RSI overbought condition.

    Args:
        df: DataFrame with indicators
        ticker: Stock ticker symbol
        threshold: RSI threshold for overbought (default: 70)

    Returns:
        Alert if RSI is overbought, None otherwise
    """
    if "RSI" not in df.columns:
        return None

    current = df.iloc[-1]
    rsi = current.get("RSI")

    if pd.notna(rsi) and rsi > threshold:
        message = format_rsi_alert(
            ticker=ticker,
            price=current["Close"],
            rsi=rsi,
            signal_type="overbought"
        )
        return Alert(
            ticker=ticker,
            alert_type="rsi_overbought",
            message=message,
            timestamp=datetime.now()
        )

    return None


def check_ticker(ticker: str) -> list[Alert]:
    """Check a single ticker for all alert conditions.

    Args:
        ticker: Stock ticker symbol

    Returns:
        List of triggered alerts
    """
    alerts = []

    try:
        # Fetch data with enough history for indicators
        df = fetch_stock_data(ticker, period="3mo")
        df = add_all_indicators(df)

        # Check all conditions
        golden_cross = check_golden_cross(df, ticker)
        if golden_cross:
            alerts.append(golden_cross)

        dead_cross = check_dead_cross(df, ticker)
        if dead_cross:
            alerts.append(dead_cross)

        rsi_oversold = check_rsi_oversold(df, ticker)
        if rsi_oversold:
            alerts.append(rsi_oversold)

        rsi_overbought = check_rsi_overbought(df, ticker)
        if rsi_overbought:
            alerts.append(rsi_overbought)

    except Exception as e:
        print(f"Error checking {ticker}: {e}")

    return alerts


def run_alert_check(watchlist_path: str | Path) -> list[Alert]:
    """Run alert check for all tickers in watchlist.

    Args:
        watchlist_path: Path to watchlist CSV file

    Returns:
        List of all triggered alerts
    """
    all_alerts = []

    try:
        tickers = load_watchlist(watchlist_path)
        print(f"Checking {len(tickers)} tickers...")

        for ticker in tickers:
            print(f"  Checking {ticker}...")
            alerts = check_ticker(ticker)
            all_alerts.extend(alerts)

    except FileNotFoundError as e:
        print(f"Error: {e}")

    return all_alerts


def send_alerts(alerts: list[Alert]) -> None:
    """Send all alerts via LINE Notify.

    Args:
        alerts: List of alerts to send
    """
    for alert in alerts:
        print(f"Sending alert: {alert.alert_type} for {alert.ticker}")
        result = send_line_notification(alert.message)

        if result.success:
            print(f"  ✓ Sent successfully")
        else:
            print(f"  ✗ Failed: {result.message}")


if __name__ == "__main__":
    # Test run
    import sys

    watchlist_path = sys.argv[1] if len(sys.argv) > 1 else "watchlist.csv"

    print(f"Running alert check with watchlist: {watchlist_path}")
    alerts = run_alert_check(watchlist_path)

    if alerts:
        print(f"\n{len(alerts)} alert(s) triggered:")
        for alert in alerts:
            print(f"  - {alert.ticker}: {alert.alert_type}")

        send_alerts(alerts)
    else:
        print("\nNo alerts triggered.")

"""Alert checker for stock watchlist."""

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
    send_notification,
)
from watchlist_manager import WatchlistManager, StockAlert


@dataclass
class Alert:
    """Represents a triggered alert."""

    ticker: str
    alert_type: str
    message: str
    timestamp: datetime


def check_golden_cross(df: pd.DataFrame, ticker: str) -> Alert | None:
    """Check for golden cross signal."""
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
    """Check for dead cross signal."""
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
    """Check for RSI oversold condition."""
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
    """Check for RSI overbought condition."""
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


def check_stock(stock: StockAlert) -> list[Alert]:
    """Check a single stock for alert conditions based on its settings.

    Args:
        stock: StockAlert with individual settings

    Returns:
        List of triggered alerts
    """
    alerts = []

    try:
        df = fetch_stock_data(stock.ticker, period="3mo")
        df = add_all_indicators(df)

        # Check cross signals if enabled
        if stock.cross_enabled:
            golden_cross = check_golden_cross(df, stock.ticker)
            if golden_cross:
                alerts.append(golden_cross)

            dead_cross = check_dead_cross(df, stock.ticker)
            if dead_cross:
                alerts.append(dead_cross)

        # Check RSI with individual thresholds
        rsi_oversold = check_rsi_oversold(df, stock.ticker, stock.rsi_oversold)
        if rsi_oversold:
            alerts.append(rsi_oversold)

        rsi_overbought = check_rsi_overbought(df, stock.ticker, stock.rsi_overbought)
        if rsi_overbought:
            alerts.append(rsi_overbought)

    except Exception as e:
        print(f"Error checking {stock.ticker}: {e}")

    return alerts


def run_alert_check(watchlist_path: str | Path) -> list[Alert]:
    """Run alert check for all stocks in watchlist.

    Args:
        watchlist_path: Path to watchlist.json file

    Returns:
        List of all triggered alerts
    """
    all_alerts = []
    watchlist_path = Path(watchlist_path)

    # Support both .json and .csv formats
    if watchlist_path.suffix == ".json" or (watchlist_path.parent / "watchlist.json").exists():
        json_path = watchlist_path if watchlist_path.suffix == ".json" else watchlist_path.parent / "watchlist.json"
        manager = WatchlistManager(json_path)
        stocks = manager.list_all()

        if not stocks:
            print("No stocks in watchlist")
            return all_alerts

        print(f"Checking {len(stocks)} stocks...")

        for stock in stocks:
            print(f"  Checking {stock.ticker}...")
            alerts = check_stock(stock)
            all_alerts.extend(alerts)
    else:
        # Fallback to CSV (legacy support)
        print("Warning: Using legacy CSV format. Consider migrating to watchlist.json")
        import csv

        tickers = []
        if watchlist_path.exists():
            with open(watchlist_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ticker = row.get("ticker", "").strip().upper()
                    if ticker:
                        tickers.append(ticker)

        print(f"Checking {len(tickers)} tickers...")

        for ticker in tickers:
            print(f"  Checking {ticker}...")
            stock = StockAlert(ticker=ticker)
            alerts = check_stock(stock)
            all_alerts.extend(alerts)

    return all_alerts


def send_alerts(alerts: list[Alert]) -> None:
    """Send all alerts via configured notification channels."""
    for alert in alerts:
        print(f"Sending alert: {alert.alert_type} for {alert.ticker}")
        result = send_notification(alert.message)

        if result.success:
            print(f"  ✓ {result.message}")
        else:
            print(f"  ✗ Failed: {result.message}")


if __name__ == "__main__":
    import sys

    # Default to watchlist.json in parent directory
    default_path = Path(__file__).parent.parent / "watchlist.json"
    watchlist_path = sys.argv[1] if len(sys.argv) > 1 else default_path

    print(f"Running alert check with watchlist: {watchlist_path}")
    alerts = run_alert_check(watchlist_path)

    if alerts:
        print(f"\n{len(alerts)} alert(s) triggered:")
        for alert in alerts:
            print(f"  - {alert.ticker}: {alert.alert_type}")

        send_alerts(alerts)
    else:
        print("\nNo alerts triggered.")

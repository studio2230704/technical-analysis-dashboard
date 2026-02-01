"""LINE Notify integration for stock alerts."""

import os
from dataclasses import dataclass

import requests


@dataclass
class NotificationResult:
    """Result of notification attempt."""

    success: bool
    message: str


def send_line_notification(message: str, token: str | None = None) -> NotificationResult:
    """Send notification via LINE Notify.

    Args:
        message: Message to send
        token: LINE Notify token. If None, reads from LINE_NOTIFY_TOKEN env var.

    Returns:
        NotificationResult with success status and message
    """
    token = token or os.getenv("LINE_NOTIFY_TOKEN")

    if not token:
        return NotificationResult(
            success=False,
            message="LINE_NOTIFY_TOKEN not configured"
        )

    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}

    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)

        if response.status_code == 200:
            return NotificationResult(success=True, message="Notification sent")
        else:
            return NotificationResult(
                success=False,
                message=f"LINE API error: {response.status_code}"
            )
    except requests.RequestException as e:
        return NotificationResult(success=False, message=f"Request failed: {e}")


def format_golden_cross_alert(ticker: str, price: float, date: str) -> str:
    """Format golden cross alert message.

    Args:
        ticker: Stock ticker symbol
        price: Current price
        date: Signal date

    Returns:
        Formatted alert message
    """
    return f"""
🟢 ゴールデンクロス検出

銘柄: {ticker}
価格: ${price:,.2f}
日付: {date}

短期移動平均線が長期移動平均線を上抜けました。
買いシグナルの可能性があります。
"""


def format_rsi_alert(
    ticker: str,
    price: float,
    rsi: float,
    signal_type: str
) -> str:
    """Format RSI alert message.

    Args:
        ticker: Stock ticker symbol
        price: Current price
        rsi: RSI value
        signal_type: "oversold" or "overbought"

    Returns:
        Formatted alert message
    """
    if signal_type == "oversold":
        emoji = "🔵"
        condition = "売られすぎ (RSI < 30)"
        suggestion = "反発の可能性があります。"
    else:
        emoji = "🔴"
        condition = "買われすぎ (RSI > 70)"
        suggestion = "調整の可能性があります。"

    return f"""
{emoji} RSIアラート

銘柄: {ticker}
価格: ${price:,.2f}
RSI: {rsi:.1f}
状態: {condition}

{suggestion}
"""


def format_dead_cross_alert(ticker: str, price: float, date: str) -> str:
    """Format dead cross alert message.

    Args:
        ticker: Stock ticker symbol
        price: Current price
        date: Signal date

    Returns:
        Formatted alert message
    """
    return f"""
🔴 デッドクロス検出

銘柄: {ticker}
価格: ${price:,.2f}
日付: {date}

短期移動平均線が長期移動平均線を下抜けました。
売りシグナルの可能性があります。
"""

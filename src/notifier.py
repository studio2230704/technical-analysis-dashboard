"""Google Chat notification for stock alerts."""

import os
from dataclasses import dataclass

import requests


@dataclass
class NotificationResult:
    """Result of notification attempt."""

    success: bool
    message: str


def send_google_chat_message(message: str, webhook_url: str | None = None) -> NotificationResult:
    """Send notification via Google Chat Webhook.

    Args:
        message: Message to send
        webhook_url: Google Chat Webhook URL. If None, reads from GOOGLE_CHAT_WEBHOOK_URL env var.

    Returns:
        NotificationResult with success status and message
    """
    webhook_url = webhook_url or os.getenv("GOOGLE_CHAT_WEBHOOK_URL")

    if not webhook_url:
        return NotificationResult(
            success=False,
            message="GOOGLE_CHAT_WEBHOOK_URL not configured"
        )

    data = {"text": message.strip()}

    try:
        response = requests.post(webhook_url, json=data, timeout=10)

        if response.status_code == 200:
            return NotificationResult(success=True, message="Message sent to Google Chat")
        else:
            return NotificationResult(
                success=False,
                message=f"Google Chat API error: {response.status_code}"
            )
    except requests.RequestException as e:
        return NotificationResult(success=False, message=f"Request failed: {e}")


# Alias for unified interface
send_notification = send_google_chat_message


def format_golden_cross_alert(ticker: str, price: float, date: str) -> str:
    """Format golden cross alert message."""
    return f"""🟢 ゴールデンクロス検出

銘柄: {ticker}
価格: ${price:,.2f}
日付: {date}

短期移動平均線が長期移動平均線を上抜けました。
買いシグナルの可能性があります。"""


def format_rsi_alert(ticker: str, price: float, rsi: float, signal_type: str) -> str:
    """Format RSI alert message."""
    if signal_type == "oversold":
        emoji = "🔵"
        condition = "売られすぎ (RSI < 30)"
        suggestion = "反発の可能性があります。"
    else:
        emoji = "🔴"
        condition = "買われすぎ (RSI > 70)"
        suggestion = "調整の可能性があります。"

    return f"""{emoji} RSIアラート

銘柄: {ticker}
価格: ${price:,.2f}
RSI: {rsi:.1f}
状態: {condition}

{suggestion}"""


def format_dead_cross_alert(ticker: str, price: float, date: str) -> str:
    """Format dead cross alert message."""
    return f"""🔴 デッドクロス検出

銘柄: {ticker}
価格: ${price:,.2f}
日付: {date}

短期移動平均線が長期移動平均線を下抜けました。
売りシグナルの可能性があります。"""

"""Notification integrations for stock alerts (LINE, Google Chat)."""

import os
from dataclasses import dataclass

import requests


@dataclass
class NotificationResult:
    """Result of notification attempt."""

    success: bool
    message: str


# =============================================================================
# Google Chat
# =============================================================================

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


# =============================================================================
# LINE Messaging API
# =============================================================================

def send_line_message(message: str, user_id: str | None = None, channel_access_token: str | None = None) -> NotificationResult:
    """Send notification via LINE Messaging API.

    Args:
        message: Message to send
        user_id: LINE user ID to send to. If None, reads from LINE_USER_ID env var.
        channel_access_token: Channel access token. If None, reads from LINE_CHANNEL_ACCESS_TOKEN env var.

    Returns:
        NotificationResult with success status and message
    """
    user_id = user_id or os.getenv("LINE_USER_ID")
    channel_access_token = channel_access_token or os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

    if not channel_access_token:
        return NotificationResult(
            success=False,
            message="LINE_CHANNEL_ACCESS_TOKEN not configured"
        )

    if not user_id:
        return NotificationResult(
            success=False,
            message="LINE_USER_ID not configured"
        )

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}"
    }
    data = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": message.strip()
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 200:
            return NotificationResult(success=True, message="Message sent")
        else:
            error_detail = response.json() if response.text else {}
            return NotificationResult(
                success=False,
                message=f"LINE API error: {response.status_code} - {error_detail}"
            )
    except requests.RequestException as e:
        return NotificationResult(success=False, message=f"Request failed: {e}")


# Alias for backward compatibility
send_line_notification = send_line_message


# =============================================================================
# Unified Notification Sender
# =============================================================================

def send_notification(message: str) -> NotificationResult:
    """Send notification to all configured channels.

    Tries Google Chat first (if configured), then LINE.
    Returns success if at least one channel succeeds.

    Args:
        message: Message to send

    Returns:
        NotificationResult with combined status
    """
    results = []

    # Try Google Chat
    if os.getenv("GOOGLE_CHAT_WEBHOOK_URL"):
        result = send_google_chat_message(message)
        results.append(("Google Chat", result))

    # Try LINE
    if os.getenv("LINE_CHANNEL_ACCESS_TOKEN") and os.getenv("LINE_USER_ID"):
        result = send_line_message(message)
        results.append(("LINE", result))

    if not results:
        return NotificationResult(
            success=False,
            message="No notification channels configured"
        )

    # Check if any succeeded
    successes = [name for name, r in results if r.success]
    failures = [f"{name}: {r.message}" for name, r in results if not r.success]

    if successes:
        return NotificationResult(
            success=True,
            message=f"Sent via: {', '.join(successes)}"
        )
    else:
        return NotificationResult(
            success=False,
            message=f"All channels failed - {'; '.join(failures)}"
        )


def format_golden_cross_alert(ticker: str, price: float, date: str) -> str:
    """Format golden cross alert message.

    Args:
        ticker: Stock ticker symbol
        price: Current price
        date: Signal date

    Returns:
        Formatted alert message
    """
    return f"""🟢 ゴールデンクロス検出

銘柄: {ticker}
価格: ${price:,.2f}
日付: {date}

短期移動平均線が長期移動平均線を上抜けました。
買いシグナルの可能性があります。"""


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

    return f"""{emoji} RSIアラート

銘柄: {ticker}
価格: ${price:,.2f}
RSI: {rsi:.1f}
状態: {condition}

{suggestion}"""


def format_dead_cross_alert(ticker: str, price: float, date: str) -> str:
    """Format dead cross alert message.

    Args:
        ticker: Stock ticker symbol
        price: Current price
        date: Signal date

    Returns:
        Formatted alert message
    """
    return f"""🔴 デッドクロス検出

銘柄: {ticker}
価格: ${price:,.2f}
日付: {date}

短期移動平均線が長期移動平均線を下抜けました。
売りシグナルの可能性があります。"""

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


def format_alert_with_order_info(
    alert_message: str,
    ticker: str,
    name: str,
    current_price: float,
    entry_price: float,
    position_shares: int,
    position_value: float,
    stop_loss_price: float,
    stop_loss_percent: float,
    take_profit_price: float,
    take_profit_percent: float,
    risk_amount: float,
    reward_amount: float,
    risk_reward_ratio: float,
) -> str:
    """アラートメッセージに発注情報を追加する。

    Args:
        alert_message: 元のアラートメッセージ
        その他: OrderInfo の各フィールド

    Returns:
        発注情報付きのアラートメッセージ
    """
    order_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 発注情報
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【銘柄】
  {name} ({ticker})

【価格】
  現在価格: ${current_price:,.2f}
  推奨エントリー: ${entry_price:,.2f}

【ポジションサイズ】
  株数: {position_shares:,} 株
  金額: ${position_value:,.2f}

【リスク管理】
  ストップロス: ${stop_loss_price:,.2f} (-{stop_loss_percent:.1f}%)
  利益確定目標: ${take_profit_price:,.2f} (+{take_profit_percent:.1f}%)

【リスクリワード】
  リスク額: ${risk_amount:,.2f}
  期待利益: ${reward_amount:,.2f}
  比率: 1:{risk_reward_ratio:.1f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    return alert_message + "\n" + order_section

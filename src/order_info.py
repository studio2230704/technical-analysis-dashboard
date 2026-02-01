"""Order information calculator for alert-triggered trades."""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from data import fetch_stock_data, get_stock_info, get_current_price
from indicators import add_all_indicators


@dataclass
class OrderInfo:
    """発注に必要な情報をまとめたデータクラス。"""

    # 銘柄情報
    ticker: str
    name: str

    # 価格情報
    current_price: float
    entry_price: float

    # ポジションサイズ
    position_size_shares: int
    position_size_value: float

    # リスク管理
    stop_loss_price: float
    stop_loss_percent: float
    take_profit_price: float
    take_profit_percent: float

    # リスクリワード
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float


def find_recent_swing_low(df: pd.DataFrame, lookback: int = 20) -> float:
    """直近のスイングロー（安値）を特定する。

    Args:
        df: OHLCV DataFrame
        lookback: 遡る日数（デフォルト: 20日）

    Returns:
        直近安値
    """
    recent = df.tail(lookback)
    return recent["Low"].min()


def calculate_order_info(
    ticker: str,
    total_assets: float,
    risk_percent: float = 2.0,
    stop_loss_buffer: float = 5.0,
    risk_reward: float = 2.0,
    lookback_days: int = 20,
) -> OrderInfo:
    """アラート発生時の発注情報を計算する。

    Args:
        ticker: ティッカーシンボル
        total_assets: 総資産額（USD）
        risk_percent: リスク許容度（%）（デフォルト: 2%）
        stop_loss_buffer: ストップロスバッファ（直近安値からの%）（デフォルト: 5%）
        risk_reward: リスクリワード比率（デフォルト: 1:2）
        lookback_days: スイングロー検出の遡り日数

    Returns:
        OrderInfo オブジェクト
    """
    # 銘柄情報を取得
    stock_info = get_stock_info(ticker)
    price_info = get_current_price(ticker)

    name = stock_info.get("name", ticker)
    current_price = price_info.get("price", 0)

    if not current_price or current_price <= 0:
        raise ValueError(f"Unable to get current price for {ticker}")

    # 株価データを取得してスイングローを計算
    df = fetch_stock_data(ticker, period="3mo")
    df = add_all_indicators(df)

    swing_low = find_recent_swing_low(df, lookback_days)

    # ストップロス価格（直近安値の5%下）
    stop_loss_price = swing_low * (1 - stop_loss_buffer / 100)
    stop_loss_percent = ((current_price - stop_loss_price) / current_price) * 100

    # リスク額（総資産の2%）
    risk_amount = total_assets * (risk_percent / 100)

    # ポジションサイズ（リスク額 ÷ 1株あたりのリスク）
    risk_per_share = current_price - stop_loss_price

    if risk_per_share <= 0:
        raise ValueError(f"Invalid stop loss: current price {current_price} is below swing low {swing_low}")

    position_size_shares = int(risk_amount / risk_per_share)
    position_size_value = position_size_shares * current_price

    # 利益確定目標（リスクリワード1:2）
    reward_amount = risk_amount * risk_reward
    profit_per_share = risk_per_share * risk_reward
    take_profit_price = current_price + profit_per_share
    take_profit_percent = (profit_per_share / current_price) * 100

    return OrderInfo(
        ticker=ticker,
        name=name,
        current_price=current_price,
        entry_price=current_price,  # 成行の場合は現在価格
        position_size_shares=position_size_shares,
        position_size_value=position_size_value,
        stop_loss_price=stop_loss_price,
        stop_loss_percent=stop_loss_percent,
        take_profit_price=take_profit_price,
        take_profit_percent=take_profit_percent,
        risk_amount=risk_amount,
        reward_amount=reward_amount,
        risk_reward_ratio=risk_reward,
    )


def format_order_info(order: OrderInfo) -> str:
    """発注情報を見やすい形式でフォーマットする。

    Args:
        order: OrderInfo オブジェクト

    Returns:
        フォーマットされた文字列
    """
    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 発注情報
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【銘柄】
  {order.name} ({order.ticker})

【価格】
  現在価格: ${order.current_price:,.2f}
  推奨エントリー: ${order.entry_price:,.2f}

【ポジションサイズ】
  株数: {order.position_size_shares:,} 株
  金額: ${order.position_size_value:,.2f}

【リスク管理】
  ストップロス: ${order.stop_loss_price:,.2f} (-{order.stop_loss_percent:.1f}%)
  利益確定目標: ${order.take_profit_price:,.2f} (+{order.take_profit_percent:.1f}%)

【リスクリワード】
  リスク額: ${order.risk_amount:,.2f}
  期待利益: ${order.reward_amount:,.2f}
  比率: 1:{order.risk_reward_ratio:.1f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""


def format_order_info_compact(order: OrderInfo) -> str:
    """発注情報をコンパクトな形式でフォーマットする（通知用）。

    Args:
        order: OrderInfo オブジェクト

    Returns:
        フォーマットされた文字列
    """
    return f"""📊 発注情報: {order.name} ({order.ticker})

💰 価格: ${order.current_price:,.2f} → エントリー: ${order.entry_price:,.2f}
📦 ポジション: {order.position_size_shares:,}株 (${order.position_size_value:,.2f})
🛑 SL: ${order.stop_loss_price:,.2f} (-{order.stop_loss_percent:.1f}%)
🎯 TP: ${order.take_profit_price:,.2f} (+{order.take_profit_percent:.1f}%)
⚖️ R:R = 1:{order.risk_reward_ratio:.1f}"""


if __name__ == "__main__":
    import sys

    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    total_assets = float(sys.argv[2]) if len(sys.argv) > 2 else 100000

    print(f"Calculating order info for {ticker}...")
    print(f"Total assets: ${total_assets:,.2f}")
    print()

    try:
        order = calculate_order_info(ticker, total_assets)
        print(format_order_info(order))
    except Exception as e:
        print(f"Error: {e}")

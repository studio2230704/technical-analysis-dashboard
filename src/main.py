"""Technical Analysis Dashboard - Main Entry Point."""

import streamlit as st
import pandas as pd

from data import fetch_stock_data, get_stock_info, get_current_price
from indicators import add_all_indicators
from signals import detect_all_signals, Signal
from charts import create_candlestick_chart


# Page configuration
st.set_page_config(
    page_title="テクニカル分析ダッシュボード",
    page_icon="📈",
    layout="wide",
)

st.title("📈 テクニカル分析ダッシュボード")

# Sidebar
with st.sidebar:
    st.header("設定")

    ticker = st.text_input(
        "ティッカーシンボル",
        value="NVDA",
        placeholder="例: AAPL, NVDA, 7203.T",
        help="米国株はそのまま、日本株は.Tを付ける（例: 7203.T）",
    ).upper().strip()

    period = st.selectbox(
        "期間",
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=3,
        format_func=lambda x: {
            "1mo": "1ヶ月",
            "3mo": "3ヶ月",
            "6mo": "6ヶ月",
            "1y": "1年",
            "2y": "2年",
            "5y": "5年",
        }.get(x, x),
    )

    st.subheader("表示設定")

    # 移動平均線の個別設定
    with st.expander("移動平均線", expanded=True):
        show_ma5 = st.checkbox("MA5 (5日)", value=True)
        show_ma25 = st.checkbox("MA25 (25日)", value=True)
        show_ma75 = st.checkbox("MA75 (75日)", value=True)
        show_ma200 = st.checkbox("MA200 (200日)", value=True)

    show_bb = st.checkbox("ボリンジャーバンド", value=True)

    # 移動平均線の設定を辞書にまとめる
    ma_settings = {
        "SMA_5": show_ma5,
        "SMA_25": show_ma25,
        "SMA_75": show_ma75,
        "SMA_200": show_ma200,
    }

    analyze_btn = st.button("分析開始", type="primary", use_container_width=True)


@st.cache_data(ttl=300)
def load_data(ticker: str, period: str):
    """Load and cache stock data."""
    try:
        df = fetch_stock_data(ticker, period)
        df = add_all_indicators(df)
        info = get_stock_info(ticker)
        return df, info, None
    except Exception as e:
        return None, None, str(e)


def display_signals(signals: list[Signal]):
    """Display signal list."""
    if not signals:
        st.info("直近30日間にシグナルはありません")
        return

    for signal in signals[:10]:  # Show latest 10
        icon = "🟢" if signal.is_bullish else "🔴"
        st.markdown(
            f"{icon} **{signal.date}** - {signal.description} (${signal.price:.2f})"
        )


def display_current_indicators(df: pd.DataFrame):
    """Display current indicator values."""
    if df.empty:
        return

    latest = df.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rsi_val = latest.get("RSI")
        if pd.notna(rsi_val):
            rsi_status = "売られすぎ" if rsi_val < 30 else "買われすぎ" if rsi_val > 70 else "中立"
            st.metric("RSI", f"{rsi_val:.1f}", rsi_status)

    with col2:
        macd_val = latest.get("MACD")
        signal_val = latest.get("MACD_Signal")
        if pd.notna(macd_val) and pd.notna(signal_val):
            diff = macd_val - signal_val
            status = "買い" if diff > 0 else "売り"
            st.metric("MACD", f"{macd_val:.2f}", status)

    with col3:
        bb_upper = latest.get("BB_Upper")
        bb_lower = latest.get("BB_Lower")
        close = latest.get("Close")
        if pd.notna(bb_upper) and pd.notna(bb_lower) and pd.notna(close):
            bb_pos = (close - bb_lower) / (bb_upper - bb_lower) * 100
            st.metric("BB位置", f"{bb_pos:.0f}%", "上限付近" if bb_pos > 80 else "下限付近" if bb_pos < 20 else "中間")

    with col4:
        sma_25 = latest.get("SMA_25")
        sma_75 = latest.get("SMA_75")
        if pd.notna(sma_25) and pd.notna(sma_75):
            trend = "上昇トレンド" if sma_25 > sma_75 else "下降トレンド"
            st.metric("トレンド", trend)


# Main content
if analyze_btn or ticker:
    if not ticker:
        st.warning("ティッカーシンボルを入力してください")
    else:
        with st.spinner(f"{ticker} のデータを取得中..."):
            df, info, error = load_data(ticker, period)

        if error:
            st.error(f"エラー: {error}")
        elif df is None or df.empty:
            st.error(f"{ticker} のデータが見つかりません")
        else:
            # Header with stock info
            st.header(f"{info.get('name', ticker)} ({ticker})")

            # Current price info
            try:
                price_info = get_current_price(ticker)
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    price = price_info.get("price")
                    change_pct = price_info.get("change_percent")
                    if price:
                        st.metric(
                            "現在値",
                            f"${price:,.2f}" if info.get("currency") == "USD" else f"¥{price:,.0f}",
                            f"{change_pct:+.2f}%" if change_pct else None,
                        )

                with col2:
                    st.metric("52週高値", f"${info.get('52w_high', 0):,.2f}")

                with col3:
                    st.metric("52週安値", f"${info.get('52w_low', 0):,.2f}")

                with col4:
                    pe = info.get("pe_ratio")
                    st.metric("PER", f"{pe:.1f}" if pe else "N/A")
            except Exception:
                pass

            st.divider()

            # Current Indicators
            st.subheader("📊 現在のテクニカル指標")
            display_current_indicators(df)

            st.divider()

            # Chart
            st.subheader("📉 チャート")
            fig = create_candlestick_chart(df, ticker, ma_settings, show_bb)
            st.plotly_chart(fig, use_container_width=True)

            st.divider()

            # Signals
            st.subheader("🎯 シグナル検出（直近30日）")
            signals = detect_all_signals(df, lookback_days=30)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**買いシグナル**")
                bullish = [s for s in signals if s.is_bullish]
                display_signals(bullish)

            with col2:
                st.markdown("**売りシグナル**")
                bearish = [s for s in signals if not s.is_bullish]
                display_signals(bearish)

            st.divider()

            # Data Table
            with st.expander("📋 詳細データ"):
                display_cols = [
                    "Open", "High", "Low", "Close", "Volume",
                    "SMA_5", "SMA_25", "SMA_75", "SMA_200",
                    "RSI", "MACD", "MACD_Signal",
                    "BB_Upper", "BB_Lower",
                ]
                available_cols = [c for c in display_cols if c in df.columns]
                st.dataframe(
                    df[available_cols].tail(30).sort_index(ascending=False),
                    use_container_width=True,
                )

# Footer
st.divider()
st.caption(
    "データソース: Yahoo Finance | "
    "免責事項: 本ツールは情報提供を目的としており、投資助言ではありません。"
)

"""Technical Analysis Dashboard - Main Entry Point."""

import streamlit as st
import pandas as pd
from pathlib import Path

from data import fetch_stock_data, get_stock_info, get_current_price
from indicators import add_all_indicators
from signals import detect_all_signals, Signal
from charts import create_candlestick_chart
from watchlist_manager import WatchlistManager, StockAlert


# Page configuration
st.set_page_config(
    page_title="テクニカル分析ダッシュボード",
    page_icon="📈",
    layout="wide",
)

st.title("📈 テクニカル分析ダッシュボード")

# Tab navigation
tab1, tab2 = st.tabs(["📊 テクニカル分析", "🔔 アラート設定"])


# =============================================================================
# Tab 1: Technical Analysis
# =============================================================================
with tab1:
    # Sidebar for Technical Analysis
    with st.sidebar:
        st.header("分析設定")

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

        with st.expander("移動平均線", expanded=True):
            show_ma5 = st.checkbox("MA5 (5日)", value=True)
            show_ma25 = st.checkbox("MA25 (25日)", value=True)
            show_ma75 = st.checkbox("MA75 (75日)", value=True)
            show_ma200 = st.checkbox("MA200 (200日)", value=True)

        show_bb = st.checkbox("ボリンジャーバンド", value=True)

        ma_settings = {
            "SMA_5": show_ma5,
            "SMA_25": show_ma25,
            "SMA_75": show_ma75,
            "SMA_200": show_ma200,
        }

        analyze_btn = st.button("分析開始", type="primary", use_container_width=True)

    @st.cache_data(ttl=300)
    def load_data(ticker: str, period: str):
        try:
            df = fetch_stock_data(ticker, period)
            df = add_all_indicators(df)
            info = get_stock_info(ticker)
            return df, info, None
        except Exception as e:
            return None, None, str(e)

    def display_signals(signals: list[Signal]):
        if not signals:
            st.info("直近30日間にシグナルはありません")
            return
        for signal in signals[:10]:
            icon = "🟢" if signal.is_bullish else "🔴"
            st.markdown(f"{icon} **{signal.date}** - {signal.description} (${signal.price:.2f})")

    def display_current_indicators(df: pd.DataFrame):
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
                st.header(f"{info.get('name', ticker)} ({ticker})")

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

                st.subheader("📊 現在のテクニカル指標")
                display_current_indicators(df)

                st.divider()

                st.subheader("📉 チャート")
                fig = create_candlestick_chart(df, ticker, ma_settings, show_bb)
                st.plotly_chart(fig, use_container_width=True)

                st.divider()

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


# =============================================================================
# Tab 2: Alert Settings
# =============================================================================
with tab2:
    st.header("🔔 アラート設定")
    st.caption("監視銘柄の管理とアラート条件の設定")

    # Initialize watchlist manager
    WATCHLIST_PATH = Path(__file__).parent.parent / "watchlist.json"
    manager = WatchlistManager(WATCHLIST_PATH)

    # Add Stock Section
    st.subheader("銘柄を追加")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        new_ticker = st.text_input(
            "ティッカーシンボル",
            placeholder="例: AAPL, 7203.T",
            key="new_ticker_alert"
        ).upper().strip()

    with col2:
        new_name = st.text_input(
            "銘柄名（任意）",
            placeholder="例: Apple Inc.",
            key="new_name_alert"
        )

    with col3:
        st.write("")
        st.write("")
        add_btn = st.button("追加", type="primary", use_container_width=True, key="add_stock_btn")

    if add_btn and new_ticker:
        if new_ticker in manager:
            st.error(f"{new_ticker} は既に登録されています")
        else:
            name = new_name
            if not name:
                try:
                    info = get_stock_info(new_ticker)
                    name = info.get("name", "")
                except Exception:
                    name = ""
            stock = StockAlert(ticker=new_ticker, name=name)
            manager.add(stock)
            st.success(f"{new_ticker} を追加しました")
            st.rerun()

    # Watchlist Table
    st.subheader("監視銘柄一覧")

    stocks = manager.list_all()

    if not stocks:
        st.info("監視銘柄がありません。上のフォームから追加してください。")
    else:
        df_data = []
        for stock in stocks:
            df_data.append({
                "ティッカー": stock.ticker,
                "銘柄名": stock.name,
                "RSI売られすぎ": stock.rsi_oversold,
                "RSI買われすぎ": stock.rsi_overbought,
                "クロス検出": stock.cross_enabled,
            })

        df_watchlist = pd.DataFrame(df_data)

        edited_df = st.data_editor(
            df_watchlist,
            column_config={
                "ティッカー": st.column_config.TextColumn("ティッカー", disabled=True, width="small"),
                "銘柄名": st.column_config.TextColumn("銘柄名", width="medium"),
                "RSI売られすぎ": st.column_config.NumberColumn("RSI売られすぎ", min_value=0, max_value=50, step=5, width="small"),
                "RSI買われすぎ": st.column_config.NumberColumn("RSI買われすぎ", min_value=50, max_value=100, step=5, width="small"),
                "クロス検出": st.column_config.CheckboxColumn("クロス検出", width="small"),
            },
            hide_index=True,
            use_container_width=True,
            key="watchlist_editor",
        )

        if st.button("変更を保存", type="primary", key="save_watchlist_btn"):
            for _, row in edited_df.iterrows():
                ticker_val = row["ティッカー"]
                manager.update(
                    ticker_val,
                    name=row["銘柄名"],
                    rsi_oversold=int(row["RSI売られすぎ"]),
                    rsi_overbought=int(row["RSI買われすぎ"]),
                    cross_enabled=bool(row["クロス検出"]),
                )
            st.success("設定を保存しました")

        # Delete Stock
        st.subheader("銘柄を削除")

        col1, col2 = st.columns([3, 1])

        with col1:
            delete_ticker = st.selectbox(
                "削除する銘柄",
                options=[s.ticker for s in stocks],
                format_func=lambda x: f"{x} - {manager.get(x).name}" if manager.get(x) and manager.get(x).name else x,
                key="delete_ticker_select"
            )

        with col2:
            st.write("")
            st.write("")
            if st.button("削除", type="secondary", key="delete_stock_btn"):
                if delete_ticker:
                    manager.remove(delete_ticker)
                    st.success(f"{delete_ticker} を削除しました")
                    st.rerun()

    # Google Chat Settings
    st.subheader("Google Chat設定")

    with st.expander("Google Chat Webhookの設定方法"):
        st.markdown("""
        1. Google Chatでスペースを開く（または新規作成）
        2. スペース名をクリック → **「アプリと統合」**
        3. **「Webhookを追加」** をクリック
        4. 名前を入力（例: Stock Alert）
        5. 表示されたURLをコピーして `.env` ファイルに設定

        ```
        GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/XXXXX/messages?key=...
        ```

        ⚠️ Streamlit Cloudでは通知テストはローカル環境でのみ実行できます。
        """)


# Footer
st.divider()
st.caption(
    "データソース: Yahoo Finance | "
    "免責事項: 本ツールは情報提供を目的としており、投資助言ではありません。"
)

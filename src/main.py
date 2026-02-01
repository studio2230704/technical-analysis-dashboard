"""Technical Analysis Dashboard - Main Entry Point."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

from data import fetch_stock_data, get_stock_info, get_current_price
from indicators import add_all_indicators
from signals import detect_all_signals, Signal
from charts import create_candlestick_chart
from watchlist_manager import WatchlistManager, StockAlert
from backtest import run_backtest_single, run_backtest_portfolio, get_sp500_tickers

# Fundamental analysis imports
from fundamental.parser import FinancialParser
from fundamental.metrics import calculate_growth_metrics, calculate_all_cagrs
from fundamental.transformer import financials_to_dataframe, growth_metrics_to_dataframe, format_currency, format_percentage
from fundamental.charts import create_financials_chart, create_growth_chart, create_margin_chart

# AI analysis imports
from ai_analyzer import (
    analyze_fundamental,
    analyze_macro,
    analyze_risk,
    generate_investment_summary,
    is_api_key_configured,
)


# Page configuration
st.set_page_config(
    page_title="株式分析ダッシュボード",
    page_icon="📈",
    layout="wide",
)

# Page titles mapping
PAGE_TITLES = {
    "technical": "📊 テクニカル分析",
    "fundamental": "📋 ファンダメンタル分析",
    "ai_analysis": "🤖 AI分析",
    "alerts": "🔔 アラート設定",
    "backtest": "📈 バックテスト",
}

# =============================================================================
# Sidebar: Navigation & Common Settings
# =============================================================================
with st.sidebar:
    # Page navigation at the top
    st.header("ページ切り替え")
    page = st.radio(
        "表示画面",
        options=["technical", "fundamental", "ai_analysis", "alerts", "backtest"],
        format_func=lambda x: PAGE_TITLES.get(x, x),
        horizontal=True,
        label_visibility="collapsed",
    )

# Dynamic page title
st.title(PAGE_TITLES.get(page, "📈 株式分析ダッシュボード"))

with st.sidebar:

    st.divider()

    # Common ticker input (used across all pages)
    st.header("銘柄設定")
    ticker = st.text_input(
        "ティッカーシンボル",
        value="NVDA",
        placeholder="例: AAPL, NVDA, MSFT",
        help="米国株のティッカーシンボルを入力（ファンダメンタル分析は米国株のみ対応）",
    ).upper().strip()

    # Store ticker in session state for cross-page access
    st.session_state["ticker"] = ticker


# =============================================================================
# Helper Functions
# =============================================================================
@st.cache_data(ttl=300)
def load_data(ticker: str, period: str):
    try:
        df = fetch_stock_data(ticker, period)
        df = add_all_indicators(df)
        info = get_stock_info(ticker)
        return df, info, None
    except Exception as e:
        return None, None, str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def load_fundamental_data(ticker: str, years: int = 5):
    """Load fundamental data from SEC EDGAR."""
    try:
        parser = FinancialParser()
        financials = parser.get_company_financials(ticker, years)
        return financials, None
    except Exception as e:
        return None, str(e)


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


# =============================================================================
# Page: Technical Analysis
# =============================================================================
if page == "technical":
    # Additional sidebar settings for analysis
    with st.sidebar:
        st.divider()
        st.header("分析設定")

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
# Page: Fundamental Analysis
# =============================================================================
elif page == "fundamental":
    st.header("📋 ファンダメンタル分析")
    st.caption("SEC EDGAR 10-K年次報告書からの財務データ分析")

    # Sidebar settings
    with st.sidebar:
        st.divider()
        st.header("分析設定")

        years = st.slider(
            "取得年数",
            min_value=3,
            max_value=10,
            value=5,
            help="過去何年分の10-K報告書を取得するか",
        )

        fetch_btn = st.button("データ取得", type="primary", use_container_width=True)

    # Main content
    if not ticker:
        st.warning("サイドバーでティッカーシンボルを入力してください")
    elif fetch_btn or ("fundamental_data" in st.session_state and st.session_state.get("fundamental_ticker") == ticker):
        with st.spinner(f"{ticker} の10-K報告書を取得中... (初回は時間がかかります)"):
            financials, error = load_fundamental_data(ticker, years)

        if error:
            st.error(f"エラー: {error}")
            st.info("💡 ヒント: 米国上場企業のティッカーシンボルを入力してください（例: AAPL, MSFT, GOOGL）")
        elif financials is None or not financials.financials:
            st.error(f"{ticker} の財務データが見つかりません")
        else:
            # Store in session state for persistence
            st.session_state["fundamental_data"] = financials
            st.session_state["fundamental_ticker"] = ticker

            st.header(f"{financials.company_name} ({financials.ticker})")

            # Convert to DataFrames
            fin_df = financials_to_dataframe(financials)
            growth_metrics = calculate_growth_metrics(financials)
            growth_df = growth_metrics_to_dataframe(growth_metrics)
            cagrs = calculate_all_cagrs(financials)

            # CAGR Summary
            st.subheader("📈 年平均成長率 (CAGR)")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                cagr_val = cagrs.get("revenue_cagr")
                st.metric(
                    "売上高 CAGR",
                    format_percentage(cagr_val),
                    delta_color="normal" if cagr_val and cagr_val > 0 else "inverse",
                )

            with col2:
                cagr_val = cagrs.get("operating_income_cagr")
                st.metric(
                    "営業利益 CAGR",
                    format_percentage(cagr_val),
                    delta_color="normal" if cagr_val and cagr_val > 0 else "inverse",
                )

            with col3:
                cagr_val = cagrs.get("net_income_cagr")
                st.metric(
                    "純利益 CAGR",
                    format_percentage(cagr_val),
                    delta_color="normal" if cagr_val and cagr_val > 0 else "inverse",
                )

            with col4:
                cagr_val = cagrs.get("operating_cash_flow_cagr")
                st.metric(
                    "営業CF CAGR",
                    format_percentage(cagr_val),
                    delta_color="normal" if cagr_val and cagr_val > 0 else "inverse",
                )

            st.divider()

            # Financial Charts
            st.subheader("💹 財務指標推移")
            fig_financials = create_financials_chart(fin_df)
            st.plotly_chart(fig_financials, use_container_width=True)

            st.divider()

            # Growth Chart
            if not growth_df.empty:
                st.subheader("📊 前年比成長率")
                fig_growth = create_growth_chart(growth_df)
                st.plotly_chart(fig_growth, use_container_width=True)

                st.divider()

            # Margin Chart
            st.subheader("📉 利益率推移")
            fig_margin = create_margin_chart(fin_df)
            st.plotly_chart(fig_margin, use_container_width=True)

            st.divider()

            # Data Tables
            with st.expander("📋 財務データ詳細"):
                # Format the dataframe for display
                display_df = fin_df.copy()
                for col in ["Revenue", "Operating Income", "Net Income", "Operating Cash Flow"]:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: format_currency(x) if pd.notna(x) else "N/A")
                for col in ["Operating Margin (%)", "Net Margin (%)"]:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")

                st.dataframe(display_df, use_container_width=True, hide_index=True)

            if not growth_df.empty:
                with st.expander("📊 成長率データ詳細"):
                    display_growth_df = growth_df.copy()
                    for col in growth_df.columns:
                        if "Growth" in col:
                            display_growth_df[col] = display_growth_df[col].apply(
                                lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A"
                            )
                    st.dataframe(display_growth_df, use_container_width=True, hide_index=True)

    else:
        st.info("👆 サイドバーの「データ取得」ボタンをクリックして財務データを取得してください")

        st.markdown("""
        ### このページでできること

        SEC EDGAR（米国証券取引委員会）から10-K年次報告書を取得し、以下の財務指標を分析します：

        - **売上高** (Revenue)
        - **営業利益** (Operating Income)
        - **純利益** (Net Income)
        - **営業キャッシュフロー** (Operating Cash Flow)

        また、以下の分析指標も自動計算されます：
        - 前年比成長率 (YoY Growth)
        - 年平均成長率 (CAGR)
        - 営業利益率・純利益率

        ⚠️ **注意**: 米国上場企業のみ対応しています。
        """)


# =============================================================================
# Page: AI Analysis
# =============================================================================
elif page == "ai_analysis":
    st.header("🤖 AI分析")
    st.caption("Claude APIを使った包括的な投資分析（ファンダメンタル・マクロ・リスク評価）")

    # Check API key
    if not is_api_key_configured():
        st.error("⚠️ ANTHROPIC_API_KEY が設定されていません")
        st.markdown("""
        ### 設定方法

        **ローカル環境の場合:**
        `.env` ファイルに以下を追加:
        ```
        ANTHROPIC_API_KEY=sk-ant-xxxxx
        ```

        **Streamlit Cloud の場合:**
        1. アプリの Settings → Secrets
        2. 以下を追加:
        ```toml
        ANTHROPIC_API_KEY = "sk-ant-xxxxx"
        ```

        APIキーは [Anthropic Console](https://console.anthropic.com/) から取得できます。
        """)
    else:
        # Sidebar settings
        with st.sidebar:
            st.divider()
            st.header("AI分析設定")

            analysis_types = st.multiselect(
                "実行する分析",
                options=["fundamental", "macro", "risk"],
                default=["fundamental", "macro", "risk"],
                format_func=lambda x: {
                    "fundamental": "📊 ファンダメンタル分析",
                    "macro": "🌍 マクロ環境分析",
                    "risk": "⚠️ リスク評価",
                }.get(x, x),
            )

            generate_summary = st.checkbox("📝 総合サマリーを生成", value=True)

            st.info(f"🎯 対象銘柄: **{ticker}**")

            run_ai_btn = st.button("🚀 AI分析を実行", type="primary", use_container_width=True)

        # Main content
        if not ticker:
            st.warning("サイドバーでティッカーシンボルを入力してください")
        elif run_ai_btn:
            # Get company info
            try:
                info = get_stock_info(ticker)
                company_name = info.get("name", ticker)
                sector = info.get("sector", "Technology")
            except Exception:
                company_name = ticker
                sector = "Technology"

            # Get financial data for context
            financial_context = ""
            try:
                with st.spinner("財務データを取得中..."):
                    financials, _ = load_fundamental_data(ticker, 5)
                    if financials and financials.financials:
                        fin_df = financials_to_dataframe(financials)
                        financial_context = fin_df.to_string()
            except Exception:
                financial_context = "財務データの取得に失敗しました"

            st.header(f"{company_name} ({ticker})")

            # Store results
            results = {}

            # Run analyses
            progress = st.progress(0, text="分析を開始...")

            total_steps = len(analysis_types) + (1 if generate_summary else 0)
            current_step = 0

            if "fundamental" in analysis_types:
                with st.spinner("📊 ファンダメンタル分析を実行中..."):
                    progress.progress(current_step / total_steps, text="ファンダメンタル分析中...")
                    result = analyze_fundamental(ticker, company_name, financial_context)
                    results["fundamental"] = result
                current_step += 1

            if "macro" in analysis_types:
                with st.spinner("🌍 マクロ環境分析を実行中..."):
                    progress.progress(current_step / total_steps, text="マクロ環境分析中...")
                    result = analyze_macro(ticker, company_name, sector)
                    results["macro"] = result
                current_step += 1

            if "risk" in analysis_types:
                with st.spinner("⚠️ リスク評価を実行中..."):
                    progress.progress(current_step / total_steps, text="リスク評価中...")
                    result = analyze_risk(ticker, company_name, financial_context)
                    results["risk"] = result
                current_step += 1

            # Generate summary if all analyses succeeded
            if generate_summary and all(r.success for r in results.values() if r):
                with st.spinner("📝 総合サマリーを生成中..."):
                    progress.progress(current_step / total_steps, text="総合サマリー生成中...")
                    summary_result = generate_investment_summary(
                        ticker=ticker,
                        company_name=company_name,
                        fundamental_analysis=results.get("fundamental", {}).content if "fundamental" in results else "未実行",
                        macro_analysis=results.get("macro", {}).content if "macro" in results else "未実行",
                        risk_assessment=results.get("risk", {}).content if "risk" in results else "未実行",
                    )
                    results["summary"] = summary_result

            progress.progress(1.0, text="分析完了!")

            st.divider()

            # Display results
            if "summary" in results and results["summary"].success:
                st.subheader("📝 投資判断サマリー")
                st.markdown(results["summary"].content)
                st.divider()

            # Use tabs for detailed analyses
            if any(k in results for k in ["fundamental", "macro", "risk"]):
                tabs = []
                tab_names = []

                if "fundamental" in results:
                    tab_names.append("📊 ファンダメンタル")
                    tabs.append(results["fundamental"])
                if "macro" in results:
                    tab_names.append("🌍 マクロ環境")
                    tabs.append(results["macro"])
                if "risk" in results:
                    tab_names.append("⚠️ リスク評価")
                    tabs.append(results["risk"])

                analysis_tabs = st.tabs(tab_names)

                for i, (tab, result) in enumerate(zip(analysis_tabs, tabs)):
                    with tab:
                        if result.success:
                            st.markdown(result.content)
                        else:
                            st.error(f"分析に失敗しました: {result.error}")

        else:
            st.info("👆 サイドバーの「AI分析を実行」ボタンをクリックして分析を開始してください")

            st.markdown("""
            ### このページでできること

            Claude AI を使って、以下の包括的な投資分析を実行します：

            #### 📊 ファンダメンタル分析
            - 売上高・利益の推移分析
            - 利益率の変化
            - キャッシュフロー分析
            - バリュエーション評価

            #### 🌍 マクロ環境分析
            - 金利環境の影響
            - 為替動向
            - 業界トレンド
            - 規制環境・地政学リスク

            #### ⚠️ リスク評価
            - バリュエーションリスク
            - 業績リスク
            - マクロリスク
            - 競合・規制リスク

            #### 📝 総合サマリー
            - 上記分析を統合したSWOT分析
            - 投資判断のポイント

            ⚠️ **免責事項**: AI分析は情報提供のみを目的としており、投資助言ではありません。
            """)


# =============================================================================
# Page: Alert Settings
# =============================================================================
elif page == "alerts":
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


# =============================================================================
# Page: Backtest
# =============================================================================
elif page == "backtest":
    st.header("📈 ゴールデンクロス戦略 バックテスト")
    st.caption("移動平均線クロスオーバー戦略の過去検証")

    # Sidebar settings for backtest
    with st.sidebar:
        st.divider()
        st.header("バックテスト設定")

        test_mode = st.radio(
            "テストモード",
            options=["single", "portfolio"],
            format_func=lambda x: "単一銘柄" if x == "single" else "複数銘柄（S&P 500）",
            key="backtest_mode"
        )

        if test_mode == "single":
            st.info(f"🎯 対象銘柄: **{ticker}**")

        if test_mode == "portfolio":
            sample_size = st.slider("サンプル銘柄数", min_value=10, max_value=100, value=50, step=10, key="sample_size")

        st.subheader("戦略パラメータ")
        short_ma = st.number_input("短期移動平均（日）", min_value=5, max_value=50, value=25, key="short_ma")
        long_ma = st.number_input("長期移動平均（日）", min_value=20, max_value=200, value=75, key="long_ma")

        test_period = st.selectbox(
            "テスト期間",
            options=["1y", "2y", "3y", "5y"],
            index=3,
            format_func=lambda x: {"1y": "1年", "2y": "2年", "3y": "3年", "5y": "5年"}.get(x, x),
            key="test_period"
        )

        run_backtest_btn = st.button("バックテスト実行", type="primary", use_container_width=True, key="run_backtest")

    @st.cache_data(ttl=600, show_spinner=False)
    def cached_backtest_portfolio(tickers_tuple, period, max_stocks):
        tickers = list(tickers_tuple)
        return run_backtest_portfolio(tickers, period, max_stocks)

    @st.cache_data(ttl=600, show_spinner=False)
    def cached_backtest_single(ticker, period):
        return run_backtest_single(ticker, period)

    if run_backtest_btn:
        if test_mode == "single":
            # Use the ticker from sidebar
            bt_ticker = ticker
            if not bt_ticker:
                st.warning("サイドバーでティッカーシンボルを入力してください")
            else:
                with st.spinner(f"{bt_ticker} のバックテストを実行中..."):
                    result = cached_backtest_single(bt_ticker, test_period)

                if result is None:
                    st.error("バックテストに失敗しました")
                else:
                    st.subheader(f"{bt_ticker} バックテスト結果")

                    # Metrics
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("総取引数", result.total_trades)
                    with col2:
                        st.metric("勝率", f"{result.win_rate:.1f}%")
                    with col3:
                        st.metric("平均リターン", f"{result.avg_return:.2f}%")
                    with col4:
                        st.metric("累積リターン", f"{result.total_return:.1f}%")
                    with col5:
                        st.metric("最大ドローダウン", f"{result.max_drawdown:.1f}%")

                    # Trade history
                    st.subheader("取引履歴")
                    trade_data = []
                    for t in result.trades:
                        trade_data.append({
                            "エントリー日": t.entry_date.strftime("%Y-%m-%d") if t.entry_date else "",
                            "エントリー価格": f"${t.entry_price:.2f}",
                            "決済日": t.exit_date.strftime("%Y-%m-%d") if t.exit_date else "",
                            "決済価格": f"${t.exit_price:.2f}" if t.exit_price else "",
                            "リターン": f"{t.return_pct:.2f}%" if t.return_pct else "",
                            "結果": "✅ 勝ち" if t.is_winner else "❌ 負け"
                        })
                    st.dataframe(pd.DataFrame(trade_data), use_container_width=True, hide_index=True)

        else:  # Portfolio mode
            with st.spinner(f"S&P 500（{sample_size}銘柄）のバックテストを実行中..."):
                tickers = get_sp500_tickers()
                results = cached_backtest_portfolio(tuple(tickers), test_period, sample_size)

            if "error" in results:
                st.error(f"エラー: {results['error']}")
            else:
                summary = results["summary"]

                st.subheader("S&P 500 バックテスト結果")

                # Summary metrics
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                with col1:
                    st.metric("検証銘柄数", summary["stocks_analyzed"])
                with col2:
                    st.metric("総トレード数", summary["total_trades"])
                with col3:
                    st.metric("全体勝率", f"{summary['overall_win_rate']:.1f}%")
                with col4:
                    st.metric("平均リターン/トレード", f"{summary['avg_return_per_trade']:.2f}%")
                with col5:
                    st.metric("中央値リターン", f"{summary['median_return']:.2f}%")
                with col6:
                    st.metric("最悪ドローダウン", f"{summary['avg_max_drawdown']:.2f}%")

                st.divider()

                # Performance tables
                st.subheader("銘柄別パフォーマンス")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**トップ10（累積リターン）**")
                    top_df = pd.DataFrame(results["best_performers"])
                    top_df.columns = ["ticker", "total_return", "win_rate", "total_trades"]
                    top_df["total_return"] = top_df["total_return"].apply(lambda x: f"{x:.1f}%")
                    top_df["win_rate"] = top_df["win_rate"].apply(lambda x: f"{x:.0f}%")
                    st.dataframe(top_df, use_container_width=True, hide_index=True)

                with col2:
                    st.markdown("**ワースト10（累積リターン）**")
                    worst_df = pd.DataFrame(results["worst_performers"])
                    worst_df.columns = ["ticker", "total_return", "win_rate", "total_trades"]
                    worst_df["total_return"] = worst_df["total_return"].apply(lambda x: f"{x:.1f}%")
                    worst_df["win_rate"] = worst_df["win_rate"].apply(lambda x: f"{x:.0f}%")
                    st.dataframe(worst_df, use_container_width=True, hide_index=True)

                st.divider()

                # Distribution charts
                st.subheader("リターン分布")
                col1, col2 = st.columns(2)

                all_returns = [r.total_return for r in results["all_results"]]
                all_win_rates = [r.win_rate for r in results["all_results"]]

                with col1:
                    st.markdown("**累積リターン分布**")
                    fig1 = px.histogram(
                        x=all_returns,
                        nbins=20,
                        labels={"x": "累積リターン (%)"},
                        color_discrete_sequence=["#2196f3"]
                    )
                    fig1.add_vline(x=np.mean(all_returns), line_dash="dash", line_color="red",
                                   annotation_text=f"平均: {np.mean(all_returns):.1f}%")
                    fig1.update_layout(showlegend=False, height=300)
                    st.plotly_chart(fig1, use_container_width=True)

                with col2:
                    st.markdown("**勝率分布**")
                    fig2 = px.histogram(
                        x=all_win_rates,
                        nbins=20,
                        labels={"x": "勝率 (%)"},
                        color_discrete_sequence=["#4caf50"]
                    )
                    fig2.add_vline(x=np.mean(all_win_rates), line_dash="dash", line_color="red",
                                   annotation_text=f"平均: {np.mean(all_win_rates):.1f}%")
                    fig2.update_layout(showlegend=False, height=300)
                    st.plotly_chart(fig2, use_container_width=True)


# Footer
st.divider()
st.caption(
    "データソース: Yahoo Finance, SEC EDGAR | "
    "免責事項: 本ツールは情報提供を目的としており、投資助言ではありません。"
)

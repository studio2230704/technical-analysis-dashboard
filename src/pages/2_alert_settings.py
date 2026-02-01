"""Alert Settings Page for Streamlit."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from watchlist_manager import WatchlistManager, StockAlert
from data import get_stock_info

# Page config
st.set_page_config(
    page_title="アラート設定",
    page_icon="🔔",
    layout="wide",
)

# Initialize watchlist manager
WATCHLIST_PATH = Path(__file__).parent.parent.parent / "watchlist.json"
manager = WatchlistManager(WATCHLIST_PATH)


def get_stock_name(ticker: str) -> str:
    """Get stock name from Yahoo Finance."""
    try:
        info = get_stock_info(ticker)
        return info.get("name", "")
    except Exception:
        return ""


st.title("🔔 アラート設定")
st.caption("監視銘柄の管理とアラート条件の設定")

# =============================================================================
# Add Stock Section
# =============================================================================
st.header("銘柄を追加")

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    new_ticker = st.text_input(
        "ティッカーシンボル",
        placeholder="例: AAPL, 7203.T",
        key="new_ticker"
    ).upper().strip()

with col2:
    new_name = st.text_input(
        "銘柄名（任意）",
        placeholder="例: Apple Inc.",
        key="new_name"
    )

with col3:
    st.write("")  # Spacer
    st.write("")  # Spacer
    add_btn = st.button("追加", type="primary", use_container_width=True)

if add_btn and new_ticker:
    if new_ticker in manager:
        st.error(f"{new_ticker} は既に登録されています")
    else:
        # Get name if not provided
        name = new_name or get_stock_name(new_ticker)
        stock = StockAlert(ticker=new_ticker, name=name)
        manager.add(stock)
        st.success(f"{new_ticker} を追加しました")
        st.rerun()

# =============================================================================
# Watchlist Table Section
# =============================================================================
st.header("監視銘柄一覧")

stocks = manager.list_all()

if not stocks:
    st.info("監視銘柄がありません。上のフォームから追加してください。")
else:
    # Create editable dataframe
    df_data = []
    for stock in stocks:
        df_data.append({
            "ティッカー": stock.ticker,
            "銘柄名": stock.name,
            "RSI売られすぎ": stock.rsi_oversold,
            "RSI買われすぎ": stock.rsi_overbought,
            "クロス検出": stock.cross_enabled,
        })

    df = pd.DataFrame(df_data)

    # Editable table
    edited_df = st.data_editor(
        df,
        column_config={
            "ティッカー": st.column_config.TextColumn(
                "ティッカー",
                disabled=True,
                width="small",
            ),
            "銘柄名": st.column_config.TextColumn(
                "銘柄名",
                width="medium",
            ),
            "RSI売られすぎ": st.column_config.NumberColumn(
                "RSI売られすぎ",
                min_value=0,
                max_value=50,
                step=5,
                width="small",
            ),
            "RSI買われすぎ": st.column_config.NumberColumn(
                "RSI買われすぎ",
                min_value=50,
                max_value=100,
                step=5,
                width="small",
            ),
            "クロス検出": st.column_config.CheckboxColumn(
                "クロス検出",
                width="small",
            ),
        },
        hide_index=True,
        use_container_width=True,
        key="watchlist_editor",
    )

    # Save button
    if st.button("変更を保存", type="primary"):
        for _, row in edited_df.iterrows():
            ticker = row["ティッカー"]
            manager.update(
                ticker,
                name=row["銘柄名"],
                rsi_oversold=int(row["RSI売られすぎ"]),
                rsi_overbought=int(row["RSI買われすぎ"]),
                cross_enabled=bool(row["クロス検出"]),
            )
        st.success("設定を保存しました")

    # =============================================================================
    # Delete Stock Section
    # =============================================================================
    st.header("銘柄を削除")

    col1, col2 = st.columns([3, 1])

    with col1:
        delete_ticker = st.selectbox(
            "削除する銘柄",
            options=[s.ticker for s in stocks],
            format_func=lambda x: f"{x} - {manager.get(x).name}" if manager.get(x).name else x,
        )

    with col2:
        st.write("")  # Spacer
        st.write("")  # Spacer
        if st.button("削除", type="secondary"):
            if delete_ticker:
                manager.remove(delete_ticker)
                st.success(f"{delete_ticker} を削除しました")
                st.rerun()

# =============================================================================
# Google Chat Settings Section
# =============================================================================
st.header("Google Chat設定")

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
    """)

# =============================================================================
# Test Notification Section
# =============================================================================
st.header("通知テスト")

if st.button("テスト通知を送信"):
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / ".env")
        from notifier import send_notification

        result = send_notification("🔔 テスト通知\n\nStock Alertからのテストメッセージです。")
        if result.success:
            st.success("通知を送信しました！Google Chatを確認してください。")
        else:
            st.error(f"送信失敗: {result.message}")
    except Exception as e:
        st.error(f"エラー: {e}")

# Footer
st.divider()
st.caption("設定は自動的にwatchlist.jsonに保存されます。")

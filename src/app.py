"""Technical Analysis Dashboard - Home Page."""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="テクニカル分析ダッシュボード",
    page_icon="📈",
    layout="wide",
)

st.title("📈 テクニカル分析ダッシュボード")

st.markdown("""
株式のテクニカル分析とアラート機能を提供するダッシュボードです。

## 📊 機能

### 1. テクニカル分析
- ローソク足チャート
- 移動平均線（5日/25日/75日/200日）
- RSI（相対力指数）
- MACD
- ボリンジャーバンド
- シグナル検出（ゴールデンクロス/デッドクロスなど）

### 2. アラート設定
- 監視銘柄の追加・削除
- 銘柄ごとのRSI閾値設定
- クロス検出のオン/オフ
- Google Chat通知

## 🚀 使い方

左のサイドバーからページを選択してください：

1. **テクニカル分析** - 銘柄を入力してチャートを表示
2. **アラート設定** - 監視銘柄とアラート条件を設定

---

データソース: Yahoo Finance
""")

# Footer
st.divider()
st.caption(
    "免責事項: 本ツールは情報提供を目的としており、投資助言ではありません。"
)

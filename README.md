# Technical Analysis Dashboard

株価のテクニカル分析ダッシュボード

## 機能

- リアルタイム株価取得（yfinance）
- 移動平均線（5日、25日、75日、200日）
- RSI（相対力指数）
- MACD
- ボリンジャーバンド
- ゴールデンクロス・デッドクロス検出

## 起動

```bash
pip install -e .
streamlit run src/main.py
```

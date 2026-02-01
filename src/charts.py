"""Chart generation with Plotly."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_candlestick_chart(
    df: pd.DataFrame,
    ticker: str,
    ma_settings: dict[str, bool] | bool = True,
    show_bb: bool = True,
) -> go.Figure:
    """Create candlestick chart with indicators.

    Args:
        df: DataFrame with OHLCV and indicators
        ticker: Stock ticker symbol
        ma_settings: Dict of MA column names to show/hide, or bool to show/hide all
        show_bb: Show Bollinger Bands

    Returns:
        Plotly figure
    """
    # 後方互換性: boolが渡された場合は全てのMAに適用
    if isinstance(ma_settings, bool):
        ma_settings = {
            "SMA_5": ma_settings,
            "SMA_25": ma_settings,
            "SMA_75": ma_settings,
            "SMA_200": ma_settings,
        }
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=(
            f"{ticker} 株価チャート",
            "出来高",
            "RSI",
            "MACD",
        ),
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="価格",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )

    # Moving Averages
    ma_configs = [
        ("SMA_5", "#ff9800", "MA5"),
        ("SMA_25", "#2196f3", "MA25"),
        ("SMA_75", "#9c27b0", "MA75"),
        ("SMA_200", "#f44336", "MA200"),
    ]
    for col, color, name in ma_configs:
        if col in df.columns and ma_settings.get(col, False):
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[col],
                    mode="lines",
                    name=name,
                    line=dict(color=color, width=1),
                ),
                row=1,
                col=1,
            )

    # Bollinger Bands
    if show_bb and "BB_Upper" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["BB_Upper"],
                mode="lines",
                name="BB Upper",
                line=dict(color="rgba(128,128,128,0.5)", width=1, dash="dash"),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["BB_Lower"],
                mode="lines",
                name="BB Lower",
                line=dict(color="rgba(128,128,128,0.5)", width=1, dash="dash"),
                fill="tonexty",
                fillcolor="rgba(128,128,128,0.1)",
            ),
            row=1,
            col=1,
        )

    # Volume
    colors = [
        "#26a69a" if c >= o else "#ef5350"
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="出来高",
            marker_color=colors,
        ),
        row=2,
        col=1,
    )

    # RSI
    if "RSI" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["RSI"],
                mode="lines",
                name="RSI",
                line=dict(color="#7c4dff", width=1.5),
            ),
            row=3,
            col=1,
        )
        # Overbought/Oversold lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", row=3, col=1)

    # MACD
    if "MACD" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["MACD"],
                mode="lines",
                name="MACD",
                line=dict(color="#2196f3", width=1.5),
            ),
            row=4,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["MACD_Signal"],
                mode="lines",
                name="Signal",
                line=dict(color="#ff9800", width=1.5),
            ),
            row=4,
            col=1,
        )
        # Histogram
        colors_hist = [
            "#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_Histogram"]
        ]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["MACD_Histogram"],
                name="Histogram",
                marker_color=colors_hist,
            ),
            row=4,
            col=1,
        )
        fig.add_hline(y=0, line_dash="dot", line_color="gray", row=4, col=1)

    # Layout
    fig.update_layout(
        height=900,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    # Y-axis labels
    fig.update_yaxes(title_text="価格", row=1, col=1)
    fig.update_yaxes(title_text="出来高", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MACD", row=4, col=1)

    return fig


def create_rsi_chart(df: pd.DataFrame) -> go.Figure:
    """Create standalone RSI chart.

    Args:
        df: DataFrame with RSI column

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    if "RSI" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["RSI"],
                mode="lines",
                name="RSI",
                line=dict(color="#7c4dff", width=2),
            )
        )

    # Overbought/Oversold zones
    fig.add_hrect(y0=70, y1=100, fillcolor="red", opacity=0.1, line_width=0)
    fig.add_hrect(y0=0, y1=30, fillcolor="green", opacity=0.1, line_width=0)

    fig.add_hline(y=70, line_dash="dash", line_color="red")
    fig.add_hline(y=30, line_dash="dash", line_color="green")
    fig.add_hline(y=50, line_dash="dot", line_color="gray")

    fig.update_layout(
        height=300,
        title="RSI (Relative Strength Index)",
        yaxis=dict(range=[0, 100]),
        hovermode="x unified",
    )

    return fig

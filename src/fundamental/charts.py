"""Plotly chart generation for fundamental analysis."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def create_financials_chart(df: pd.DataFrame) -> go.Figure:
    """Create financial metrics chart.

    Args:
        df: DataFrame with financial data

    Returns:
        Plotly figure
    """
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "売上高 (Revenue)",
            "営業利益 (Operating Income)",
            "純利益 (Net Income)",
            "営業キャッシュフロー (Operating CF)",
        ),
        vertical_spacing=0.15,
        horizontal_spacing=0.1,
    )

    years = df["Fiscal Year"].astype(str)

    # Revenue
    fig.add_trace(
        go.Bar(
            x=years,
            y=df["Revenue"] / 1e9,
            name="売上高",
            marker_color="#2E86AB",
            hovertemplate="%{y:.2f}B<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Operating Income
    fig.add_trace(
        go.Bar(
            x=years,
            y=df["Operating Income"] / 1e9,
            name="営業利益",
            marker_color="#A23B72",
            hovertemplate="%{y:.2f}B<extra></extra>",
        ),
        row=1,
        col=2,
    )

    # Net Income
    fig.add_trace(
        go.Bar(
            x=years,
            y=df["Net Income"] / 1e9,
            name="純利益",
            marker_color="#F18F01",
            hovertemplate="%{y:.2f}B<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Operating Cash Flow
    fig.add_trace(
        go.Bar(
            x=years,
            y=df["Operating Cash Flow"] / 1e9,
            name="営業CF",
            marker_color="#C73E1D",
            hovertemplate="%{y:.2f}B<extra></extra>",
        ),
        row=2,
        col=2,
    )

    fig.update_layout(
        height=600,
        showlegend=False,
        title_text="財務指標 (10億ドル)",
        title_x=0.5,
    )

    # Update y-axes
    fig.update_yaxes(title_text="$B", row=1, col=1)
    fig.update_yaxes(title_text="$B", row=1, col=2)
    fig.update_yaxes(title_text="$B", row=2, col=1)
    fig.update_yaxes(title_text="$B", row=2, col=2)

    return fig


def create_growth_chart(df: pd.DataFrame) -> go.Figure:
    """Create year-over-year growth chart.

    Args:
        df: DataFrame with growth metrics

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    years = df["Fiscal Year"].astype(str)

    metrics = [
        ("Revenue Growth (%)", "#2E86AB", "売上高"),
        ("Operating Income Growth (%)", "#A23B72", "営業利益"),
        ("Net Income Growth (%)", "#F18F01", "純利益"),
        ("Operating Cash Flow Growth (%)", "#C73E1D", "営業CF"),
    ]

    for col_name, color, display_name in metrics:
        if col_name in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=years,
                    y=df[col_name],
                    mode="lines+markers",
                    name=display_name,
                    line=dict(color=color, width=2),
                    marker=dict(size=8),
                    hovertemplate=f"{display_name}: %{{y:.1f}}%<extra></extra>",
                )
            )

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="gray",
        opacity=0.5,
    )

    fig.update_layout(
        height=400,
        title_text="前年比成長率 (%)",
        title_x=0.5,
        xaxis_title="会計年度",
        yaxis_title="成長率 (%)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hovermode="x unified",
    )

    return fig


def create_margin_chart(df: pd.DataFrame) -> go.Figure:
    """Create profit margin chart.

    Args:
        df: DataFrame with margin data

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    years = df["Fiscal Year"].astype(str)

    if "Operating Margin (%)" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=years,
                y=df["Operating Margin (%)"],
                mode="lines+markers",
                name="営業利益率",
                line=dict(color="#2E86AB", width=2),
                marker=dict(size=8),
                fill="tozeroy",
                fillcolor="rgba(46, 134, 171, 0.1)",
                hovertemplate="営業利益率: %{y:.1f}%<extra></extra>",
            )
        )

    if "Net Margin (%)" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=years,
                y=df["Net Margin (%)"],
                mode="lines+markers",
                name="純利益率",
                line=dict(color="#F18F01", width=2),
                marker=dict(size=8),
                hovertemplate="純利益率: %{y:.1f}%<extra></extra>",
            )
        )

    fig.update_layout(
        height=350,
        title_text="利益率推移 (%)",
        title_x=0.5,
        xaxis_title="会計年度",
        yaxis_title="利益率 (%)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hovermode="x unified",
    )

    return fig

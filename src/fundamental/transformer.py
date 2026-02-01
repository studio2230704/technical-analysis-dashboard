"""Data transformation utilities."""

import pandas as pd

from fundamental.models import CompanyFinancials, GrowthMetrics


def financials_to_dataframe(financials: CompanyFinancials) -> pd.DataFrame:
    """Convert CompanyFinancials to pandas DataFrame.

    Args:
        financials: Company financials data

    Returns:
        DataFrame with financial data
    """
    sorted_data = financials.get_sorted_financials(ascending=True)

    records = []
    for data in sorted_data:
        records.append(
            {
                "Fiscal Year": data.fiscal_year,
                "Revenue": data.revenue,
                "Operating Income": data.operating_income,
                "Net Income": data.net_income,
                "Operating Cash Flow": data.operating_cash_flow,
                "Operating Margin (%)": data.operating_margin,
                "Net Margin (%)": data.net_margin,
            }
        )

    return pd.DataFrame(records)


def growth_metrics_to_dataframe(metrics: list[GrowthMetrics]) -> pd.DataFrame:
    """Convert growth metrics to pandas DataFrame.

    Args:
        metrics: List of growth metrics

    Returns:
        DataFrame with growth data
    """
    records = []
    for m in metrics:
        records.append(
            {
                "Fiscal Year": m.fiscal_year,
                "Revenue Growth (%)": m.revenue_growth,
                "Operating Income Growth (%)": m.operating_income_growth,
                "Net Income Growth (%)": m.net_income_growth,
                "Operating Cash Flow Growth (%)": m.operating_cash_flow_growth,
            }
        )

    return pd.DataFrame(records)


def format_currency(value: float | None, in_billions: bool = True) -> str:
    """Format a number as currency string.

    Args:
        value: Value to format
        in_billions: If True, divide by 1B and add 'B' suffix

    Returns:
        Formatted string
    """
    if value is None:
        return "N/A"

    if in_billions:
        return f"${value / 1_000_000_000:,.2f}B"
    return f"${value:,.0f}"


def format_percentage(value: float | None) -> str:
    """Format a number as percentage string.

    Args:
        value: Percentage value

    Returns:
        Formatted string
    """
    if value is None:
        return "N/A"
    return f"{value:+.1f}%"

"""Financial metrics calculations."""

from typing import Optional

from fundamental.models import CompanyFinancials, GrowthMetrics


def calculate_yoy_growth(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    """Calculate year-over-year growth percentage.

    Args:
        current: Current period value
        previous: Previous period value

    Returns:
        Growth percentage or None if calculation not possible
    """
    if current is None or previous is None or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def calculate_growth_metrics(financials: CompanyFinancials) -> list[GrowthMetrics]:
    """Calculate year-over-year growth metrics.

    Args:
        financials: Company financials data

    Returns:
        List of growth metrics for each year (except first)
    """
    sorted_data = financials.get_sorted_financials(ascending=True)

    if len(sorted_data) < 2:
        return []

    growth_list = []

    for i in range(1, len(sorted_data)):
        current = sorted_data[i]
        previous = sorted_data[i - 1]

        growth = GrowthMetrics(
            fiscal_year=current.fiscal_year,
            revenue_growth=calculate_yoy_growth(current.revenue, previous.revenue),
            operating_income_growth=calculate_yoy_growth(
                current.operating_income, previous.operating_income
            ),
            net_income_growth=calculate_yoy_growth(
                current.net_income, previous.net_income
            ),
            operating_cash_flow_growth=calculate_yoy_growth(
                current.operating_cash_flow, previous.operating_cash_flow
            ),
        )
        growth_list.append(growth)

    return growth_list


def calculate_cagr(
    start_value: Optional[float],
    end_value: Optional[float],
    years: int,
) -> Optional[float]:
    """Calculate Compound Annual Growth Rate.

    Args:
        start_value: Starting value
        end_value: Ending value
        years: Number of years

    Returns:
        CAGR as percentage or None if calculation not possible
    """
    if (
        start_value is None
        or end_value is None
        or start_value <= 0
        or years <= 0
    ):
        return None

    return (((end_value / start_value) ** (1 / years)) - 1) * 100


def calculate_all_cagrs(financials: CompanyFinancials) -> dict[str, Optional[float]]:
    """Calculate CAGR for all metrics.

    Args:
        financials: Company financials data

    Returns:
        Dictionary with CAGR for each metric
    """
    sorted_data = financials.get_sorted_financials(ascending=True)

    if len(sorted_data) < 2:
        return {
            "revenue_cagr": None,
            "operating_income_cagr": None,
            "net_income_cagr": None,
            "operating_cash_flow_cagr": None,
        }

    first = sorted_data[0]
    last = sorted_data[-1]
    years = last.fiscal_year - first.fiscal_year

    return {
        "revenue_cagr": calculate_cagr(first.revenue, last.revenue, years),
        "operating_income_cagr": calculate_cagr(
            first.operating_income, last.operating_income, years
        ),
        "net_income_cagr": calculate_cagr(first.net_income, last.net_income, years),
        "operating_cash_flow_cagr": calculate_cagr(
            first.operating_cash_flow, last.operating_cash_flow, years
        ),
    }

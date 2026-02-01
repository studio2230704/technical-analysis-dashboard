"""Fundamental analysis module using SEC EDGAR data."""

from fundamental.models import FinancialData, CompanyFinancials, GrowthMetrics
from fundamental.client import EdgarClient
from fundamental.parser import FinancialParser
from fundamental.metrics import calculate_growth_metrics, calculate_all_cagrs
from fundamental.transformer import financials_to_dataframe, growth_metrics_to_dataframe

__all__ = [
    "FinancialData",
    "CompanyFinancials",
    "GrowthMetrics",
    "EdgarClient",
    "FinancialParser",
    "calculate_growth_metrics",
    "calculate_all_cagrs",
    "financials_to_dataframe",
    "growth_metrics_to_dataframe",
]

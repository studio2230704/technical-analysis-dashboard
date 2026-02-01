"""Pydantic models for financial data."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class FinancialData(BaseModel):
    """Single fiscal year financial data."""

    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_year_end: date = Field(..., description="Fiscal year end date")
    revenue: Optional[float] = Field(None, description="Total revenue in USD")
    operating_income: Optional[float] = Field(
        None, description="Operating income in USD"
    )
    net_income: Optional[float] = Field(None, description="Net income in USD")
    operating_cash_flow: Optional[float] = Field(
        None, description="Operating cash flow in USD"
    )

    @property
    def operating_margin(self) -> Optional[float]:
        """Calculate operating margin percentage."""
        if self.revenue and self.operating_income and self.revenue != 0:
            return (self.operating_income / self.revenue) * 100
        return None

    @property
    def net_margin(self) -> Optional[float]:
        """Calculate net profit margin percentage."""
        if self.revenue and self.net_income and self.revenue != 0:
            return (self.net_income / self.revenue) * 100
        return None


class CompanyFinancials(BaseModel):
    """Company financial data across multiple years."""

    ticker: str = Field(..., description="Stock ticker symbol")
    company_name: str = Field(..., description="Company name")
    financials: list[FinancialData] = Field(
        default_factory=list, description="List of annual financial data"
    )

    def get_sorted_financials(self, ascending: bool = True) -> list[FinancialData]:
        """Get financials sorted by fiscal year."""
        return sorted(
            self.financials,
            key=lambda x: x.fiscal_year,
            reverse=not ascending,
        )


class GrowthMetrics(BaseModel):
    """Year-over-year growth metrics."""

    fiscal_year: int
    revenue_growth: Optional[float] = Field(None, description="Revenue YoY growth %")
    operating_income_growth: Optional[float] = Field(
        None, description="Operating income YoY growth %"
    )
    net_income_growth: Optional[float] = Field(
        None, description="Net income YoY growth %"
    )
    operating_cash_flow_growth: Optional[float] = Field(
        None, description="Operating cash flow YoY growth %"
    )

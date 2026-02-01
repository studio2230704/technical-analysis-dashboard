"""Parser for extracting financial data from 10-K filings."""

from datetime import date, datetime
from typing import Optional

import pandas as pd

from fundamental.client import EdgarClient
from fundamental.models import CompanyFinancials, FinancialData


def parse_date(value) -> Optional[date]:
    """Parse a date from various formats.

    Args:
        value: Date as string, date, or datetime

    Returns:
        date object or None
    """
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


class FinancialParser:
    """Parse financial data from SEC EDGAR filings."""

    def __init__(self, client: Optional[EdgarClient] = None):
        """Initialize parser with EDGAR client.

        Args:
            client: EdgarClient instance. Creates new one if not provided.
        """
        self.client = client or EdgarClient()

    def parse_10k(self, filing) -> Optional[FinancialData]:
        """Parse financial data from a single 10-K filing.

        Args:
            filing: 10-K filing object from edgartools

        Returns:
            FinancialData or None if parsing fails
        """
        try:
            xbrl = filing.xbrl()
            if xbrl is None:
                return None

            # Get filing date and fiscal year
            period_of_report = parse_date(filing.period_of_report)
            filing_date = parse_date(filing.filing_date)

            if period_of_report:
                fiscal_year = period_of_report.year
                fiscal_year_end = period_of_report
            elif filing_date:
                fiscal_year = filing_date.year
                fiscal_year_end = filing_date
            else:
                return None

            statements = xbrl.statements

            # Get income statement DataFrame
            income_df = self._get_statement_df(statements, "income")

            # Get cash flow statement DataFrame
            cashflow_df = self._get_statement_df(statements, "cashflow")

            # Extract metrics
            revenue = self._extract_metric(income_df, [
                "Revenue",
                "Revenues",
                "Total Revenue",
                "Net Revenue",
                "Total revenues",
                "Net sales",
                "Total net revenue",
            ])

            operating_income = self._extract_metric(income_df, [
                "Operating income",
                "Operating Income",
                "Income from operations",
                "Operating Income (Loss)",
            ])

            net_income = self._extract_metric(income_df, [
                "Net income",
                "Net Income",
                "Net income attributable to",
            ])

            operating_cash_flow = self._extract_metric(cashflow_df, [
                "Net cash provided by operating activities",
                "Net cash from operating activities",
                "Cash flows from operating activities",
            ])

            return FinancialData(
                fiscal_year=fiscal_year,
                fiscal_year_end=fiscal_year_end,
                revenue=revenue,
                operating_income=operating_income,
                net_income=net_income,
                operating_cash_flow=operating_cash_flow,
            )
        except Exception as e:
            print(f"Error parsing 10-K: {e}")
            return None

    def _get_statement_df(self, statements, statement_type: str) -> Optional[pd.DataFrame]:
        """Get statement as DataFrame.

        Args:
            statements: Statements object from XBRL
            statement_type: 'income' or 'cashflow'

        Returns:
            DataFrame or None
        """
        try:
            if statement_type == "income":
                stmt = statements.income_statement()
            elif statement_type == "cashflow":
                stmt = statements.cashflow_statement()
            else:
                return None

            if stmt is None:
                return None

            return stmt.to_dataframe()
        except Exception:
            return None

    def _extract_metric(
        self,
        df: Optional[pd.DataFrame],
        labels: list[str],
    ) -> Optional[float]:
        """Extract a metric value from statement DataFrame.

        Args:
            df: Statement DataFrame
            labels: List of possible label names

        Returns:
            The metric value or None
        """
        if df is None or df.empty:
            return None

        try:
            # Find the first date column (fiscal year end)
            date_cols = [c for c in df.columns if isinstance(c, str) and c.count("-") == 2]
            if not date_cols:
                return None

            value_col = date_cols[0]  # Most recent date

            # Search for matching label
            for label in labels:
                # Exact match first
                matches = df[df["label"] == label]
                if not matches.empty:
                    val = matches.iloc[0][value_col]
                    if pd.notna(val):
                        return float(val)

                # Case-insensitive match
                matches = df[df["label"].str.lower() == label.lower()]
                if not matches.empty:
                    val = matches.iloc[0][value_col]
                    if pd.notna(val):
                        return float(val)

                # Partial match (contains)
                matches = df[df["label"].str.lower().str.contains(label.lower(), na=False)]
                if not matches.empty:
                    val = matches.iloc[0][value_col]
                    if pd.notna(val):
                        return float(val)

            return None
        except Exception:
            return None

    def get_company_financials(
        self, ticker: str, years: int = 5
    ) -> CompanyFinancials:
        """Get complete financial data for a company.

        Args:
            ticker: Stock ticker symbol
            years: Number of years to fetch

        Returns:
            CompanyFinancials with parsed data
        """
        filings = self.client.get_10k_filings(ticker, years)
        company_name = self.client.get_company_name(ticker)

        financials = []
        for filing in filings:
            data = self.parse_10k(filing)
            if data is not None:
                financials.append(data)

        return CompanyFinancials(
            ticker=ticker.upper(),
            company_name=company_name,
            financials=financials,
        )

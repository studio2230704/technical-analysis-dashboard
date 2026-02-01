"""SEC EDGAR API client using edgartools."""

from typing import Optional

from edgar import Company, set_identity

from fundamental.config import get_sec_email


class EdgarClient:
    """Client for fetching SEC EDGAR filings."""

    def __init__(self, email: Optional[str] = None):
        """Initialize the EDGAR client.

        Args:
            email: Email for SEC User-Agent. Falls back to config.
        """
        identity_email = email or get_sec_email()
        set_identity(identity_email)

    def get_company(self, ticker: str) -> Company:
        """Get company by ticker symbol.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            Company object from edgartools
        """
        return Company(ticker.upper())

    def get_10k_filings(self, ticker: str, years: int = 5) -> list:
        """Get recent 10-K filings for a company.

        Args:
            ticker: Stock ticker symbol
            years: Number of years to fetch (default: 5)

        Returns:
            List of 10-K filing objects
        """
        company = self.get_company(ticker)
        filings = company.get_filings(form="10-K")

        result = []
        for filing in filings:
            if len(result) >= years:
                break
            result.append(filing)

        return result

    def get_company_name(self, ticker: str) -> str:
        """Get company name from ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Company name
        """
        company = self.get_company(ticker)
        return company.name

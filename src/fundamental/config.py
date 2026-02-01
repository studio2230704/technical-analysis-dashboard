"""Configuration for SEC EDGAR API."""

import os
from functools import lru_cache

from dotenv import load_dotenv


@lru_cache
def get_sec_email() -> str:
    """Get SEC EDGAR email from environment.

    Returns:
        Email string for SEC User-Agent header
    """
    load_dotenv()
    return os.getenv("SEC_EDGAR_EMAIL", "anonymous@example.com")

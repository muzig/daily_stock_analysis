# -*- coding: utf-8 -*-
"""
Akshare Service - Core data fetching logic
"""

import logging
import random
import time
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from utils.circuit_breaker import CircuitBreaker
from .cache_service import get_cache_service

logger = logging.getLogger(__name__)

# User-Agent pool for anti-crawling
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
]


class AkshareService:
    """Akshare data fetching service with caching and circuit breaker."""

    def __init__(self):
        self._cache = get_cache_service()
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            cooldown_seconds=300,
        )
        self._last_request_time: Optional[float] = None
        self.sleep_min = 2.0
        self.sleep_max = 5.0

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.sleep_min:
                time.sleep(self.sleep_min - elapsed)
        # Random jitter
        time.sleep(random.uniform(self.sleep_min, self.sleep_max))
        self._last_request_time = time.time()

    def _set_random_user_agent(self) -> str:
        """Return a random User-Agent."""
        return random.choice(USER_AGENTS)

    def get_daily_data(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30,
        adjust: str = "qfq",
    ) -> Tuple[Optional[pd.DataFrame], bool]:
        """
        Get daily K-line data for a stock.

        Returns:
            Tuple of (DataFrame or None, cached flag)
        """
        # Build cache key
        cache_key = self._cache.build_key("daily", {
            "code": stock_code,
            "start": start_date,
            "end": end_date,
            "days": days,
            "adjust": adjust,
        })

        # Try cache first
        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"[AkshareService] Daily data for {stock_code} found in cache")
            df = pd.DataFrame(cached_data)
            return df, True

        # Check circuit breaker
        if not self._circuit_breaker.can_execute():
            logger.warning(f"[AkshareService] Circuit breaker OPEN, skipping {stock_code}")
            return None, False

        # Fetch from akshare
        try:
            df = self._fetch_daily_data(stock_code, start_date, end_date, days, adjust)
            if df is not None and not df.empty:
                # Cache the result
                self._cache.set(cache_key, df.to_dict(orient="records"))
                self._circuit_breaker.record_success()
                return df, False
            else:
                self._circuit_breaker.record_inconclusive()
                return None, False
        except Exception as e:
            logger.error(f"[AkshareService] Failed to fetch daily data for {stock_code}: {e}")
            self._circuit_breaker.record_failure(str(e))
            return None, False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_daily_data(
        self,
        stock_code: str,
        start_date: Optional[str],
        end_date: Optional[str],
        days: int,
        adjust: str,
    ) -> Optional[pd.DataFrame]:
        """Internal method to fetch daily data from akshare."""
        import akshare as ak

        # Determine stock type and fetch accordingly
        code_upper = stock_code.upper()

        # ETF codes
        if stock_code.startswith(("51", "52", "56", "58", "15", "16", "18")):
            return self._fetch_etf_data(stock_code, start_date, end_date, adjust)
        # HK codes (5 digits)
        elif stock_code.isdigit() and len(stock_code) == 5:
            return self._fetch_hk_data(stock_code, start_date, end_date, adjust)
        # A-share codes (6 digits)
        elif stock_code.isdigit() and len(stock_code) == 6:
            return self._fetch_a_stock_data(stock_code, start_date, end_date, adjust)
        else:
            # Try A-share first
            return self._fetch_a_stock_data(stock_code, start_date, end_date, adjust)

    def _fetch_a_stock_data(
        self,
        stock_code: str,
        start_date: Optional[str],
        end_date: Optional[str],
        adjust: str,
    ) -> Optional[pd.DataFrame]:
        """Fetch A-share daily data."""
        import akshare as ak

        self._enforce_rate_limit()

        # Try Eastmoney source first
        try:
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=(start_date or "").replace("-", ""),
                end_date=(end_date or "").replace("-", ""),
                adjust=adjust,
            )
            if df is not None and not df.empty:
                return self._normalize_columns(df)
        except Exception as e:
            logger.warning(f"[AkshareService] Eastmoney fetch failed: {e}")

        # Fallback to Sina
        try:
            symbol = f"sh{stock_code}" if stock_code.startswith(("6", "5", "9")) else f"sz{stock_code}"
            df = ak.stock_zh_a_daily(
                symbol=symbol,
                start_date=(start_date or "").replace("-", ""),
                end_date=(end_date or "").replace("-", ""),
                adjust=adjust,
            )
            if df is not None and not df.empty:
                return self._normalize_columns(df)
        except Exception as e:
            logger.warning(f"[AkshareService] Sina fetch failed: {e}")

        return None

    def _fetch_etf_data(
        self,
        stock_code: str,
        start_date: Optional[str],
        end_date: Optional[str],
        adjust: str,
    ) -> Optional[pd.DataFrame]:
        """Fetch ETF daily data."""
        import akshare as ak

        self._enforce_rate_limit()

        try:
            df = ak.fund_etf_hist_em(
                symbol=stock_code,
                period="daily",
                start_date=(start_date or "").replace("-", ""),
                end_date=(end_date or "").replace("-", ""),
                adjust=adjust,
            )
            if df is not None and not df.empty:
                return self._normalize_columns(df)
        except Exception as e:
            logger.error(f"[AkshareService] ETF fetch failed: {e}")

        return None

    def _fetch_hk_data(
        self,
        stock_code: str,
        start_date: Optional[str],
        end_date: Optional[str],
        adjust: str,
    ) -> Optional[pd.DataFrame]:
        """Fetch HK stock daily data."""
        import akshare as ak

        self._enforce_rate_limit()

        # Normalize HK code to 5 digits
        code = stock_code.zfill(5)

        try:
            df = ak.stock_hk_hist(
                symbol=code,
                period="daily",
                start_date=(start_date or "").replace("-", ""),
                end_date=(end_date or "").replace("-", ""),
                adjust=adjust,
            )
            if df is not None and not df.empty:
                return self._normalize_columns(df)
        except Exception as e:
            logger.error(f"[AkshareService] HK fetch failed: {e}")

        return None

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard format."""
        column_mapping = {
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '涨跌幅': 'pct_chg',
        }
        return df.rename(columns=column_mapping)


# Singleton instance
_akshare_service: Optional[AkshareService] = None


def get_akshare_service() -> AkshareService:
    """Get AkshareService singleton."""
    global _akshare_service
    if _akshare_service is None:
        _akshare_service = AkshareService()
    return _akshare_service
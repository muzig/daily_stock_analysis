# -*- coding: utf-8 -*-
"""
===================================
AkshareProxyFetcher - 代理客户端 (Priority 0)
===================================

通过 HTTP 调用独立的 Akshare Proxy 服务获取数据。

优势：
1. 隔离第三方依赖，代理服务可独立部署和扩展
2. 内置 Redis 缓存，减少重复请求
3. 内置熔断器，避免雪崩效应
4. 可水平扩展，提高并发能力

使用条件：
- 需要配置 AKSHARE_PROXY_URL 环境变量
- 代理服务需要正常运行
"""

import logging
import os
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .base import BaseFetcher, DataFetchError, RateLimitError, STANDARD_COLUMNS
from .realtime_types import (
    UnifiedRealtimeQuote, ChipDistribution, RealtimeSource,
    get_realtime_circuit_breaker, get_chip_circuit_breaker,
    safe_float, safe_int
)

logger = logging.getLogger(__name__)


class AkshareProxyFetcher(BaseFetcher):
    """
    Akshare 代理服务客户端

    通过 HTTP 接口调用独立的代理服务获取股票数据。
    代理服务内置缓存、熔断器、重试策略。
    """

    name = "AkshareProxyFetcher"
    priority = int(os.getenv("AKSHARE_PROXY_PRIORITY", "0"))

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        初始化代理客户端

        Args:
            base_url: 代理服务地址，默认从环境变量 AKSHARE_PROXY_URL 获取
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url or os.getenv("AKSHARE_PROXY_URL", "http://localhost:8001")
        self.timeout = timeout
        self._session = requests.Session()

        # Circuit breaker for proxy service
        self._circuit_breaker = get_realtime_circuit_breaker()
        self._source_key = "akshare_proxy"

    def _check_circuit_breaker(self) -> bool:
        """检查熔断器状态"""
        if not self._circuit_breaker.is_available(self._source_key):
            logger.warning(f"[AkshareProxyFetcher] Circuit breaker OPEN for {self._source_key}")
            return False
        return True

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """
        发送 HTTP 请求到代理服务

        Args:
            endpoint: API 端点，如 /api/v1/daily
            params: 请求参数

        Returns:
            响应 JSON 数据，失败返回 None
        """
        if not self._check_circuit_breaker():
            return None

        url = f"{self.base_url.rstrip('/')}{endpoint}"

        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            self._circuit_breaker.record_success(self._source_key)
            return response.json()

        except requests.exceptions.Timeout:
            logger.warning(f"[AkshareProxyFetcher] Request timeout: {url}")
            self._circuit_breaker.record_failure(self._source_key, "timeout")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"[AkshareProxyFetcher] Request failed: {url}, error={e}")
            self._circuit_breaker.record_failure(self._source_key, str(e))
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        通过代理服务获取原始数据
        """
        params = {
            "code": stock_code,
            "start_date": start_date,
            "end_date": end_date,
            "days": 30,
        }

        result = self._make_request("/api/v1/daily", params)

        if result is None or "data" not in result:
            raise DataFetchError(f"AkshareProxyFetcher 获取 {stock_code} 数据失败")

        # Convert data list to DataFrame
        df = pd.DataFrame(result["data"])

        if df.empty:
            raise DataFetchError(f"AkshareProxyFetcher 获取 {stock_code} 数据为空")

        return df

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        标准化数据列名
        """
        df = df.copy()

        # 确保必要列存在
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise DataFetchError(f"缺少必要列: {col}")

        # 添加股票代码列
        df['code'] = stock_code

        # 只保留需要的列
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]

        return df

    def get_realtime_quote(self, stock_code: str, source: str = "em") -> Optional[UnifiedRealtimeQuote]:
        """
        获取实时行情（暂不支持，通过代理获取）
        """
        logger.debug(f"[AkshareProxyFetcher] Realtime quote not implemented via proxy, falling back to direct fetcher")
        return None

    def get_chip_distribution(self, stock_code: str) -> Optional[ChipDistribution]:
        """
        获取筹码分布（暂不支持）
        """
        logger.debug(f"[AkshareProxyFetcher] Chip distribution not implemented via proxy")
        return None

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        """获取主要指数实时行情"""
        return None

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        """获取市场涨跌统计"""
        return None

    def get_sector_rankings(self, n: int = 5) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """获取行业板块涨跌榜"""
        return None

    @property
    def is_available(self) -> bool:
        """检查代理服务是否可用"""
        try:
            response = self._session.get(
                f"{self.base_url.rstrip('/')}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False


# 注册到 DataFetcherManager 的工厂函数
def create_akshare_proxy_fetcher() -> Optional[AkshareProxyFetcher]:
    """创建 AkshareProxyFetcher 实例（如果配置了代理 URL）"""
    proxy_url = os.getenv("AKSHARE_PROXY_URL")
    if not proxy_url:
        logger.debug("[AkshareProxyFetcher] AKSHARE_PROXY_URL not configured, skipping")
        return None

    try:
        fetcher = AkshareProxyFetcher(base_url=proxy_url)
        if fetcher.is_available:
            logger.info(f"[AkshareProxyFetcher] Connected to proxy at {proxy_url}")
            return fetcher
        else:
            logger.warning(f"[AkshareProxyFetcher] Proxy at {proxy_url} is not available")
            return None
    except Exception as e:
        logger.warning(f"[AkshareProxyFetcher] Failed to create fetcher: {e}")
        return None
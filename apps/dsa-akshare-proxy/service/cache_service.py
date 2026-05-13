# -*- coding: utf-8 -*-
"""
Redis Cache Service
"""

import json
import logging
from typing import Optional, Any
import redis
from config import get_settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based cache service."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._settings = get_settings()

    @property
    def client(self) -> redis.Redis:
        """Lazy initialization of Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self._settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
            )
        return self._client

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"[Cache] HIT: {key}")
                return json.loads(value)
            logger.debug(f"[Cache] MISS: {key}")
            return None
        except Exception as e:
            logger.warning(f"[Cache] GET error for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value to cache with optional TTL."""
        try:
            ttl = ttl or self._settings.CACHE_TTL_SECONDS
            self.client.setex(key, ttl, json.dumps(value))
            logger.debug(f"[Cache] SET: {key} (TTL={ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"[Cache] SET error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            self.client.delete(key)
            logger.debug(f"[Cache] DELETE: {key}")
            return True
        except Exception as e:
            logger.warning(f"[Cache] DELETE error for {key}: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    @staticmethod
    def build_key(endpoint: str, params: dict) -> str:
        """Build cache key from endpoint and parameters."""
        params_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
        return f"akshare:{endpoint}:{params_str}"


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
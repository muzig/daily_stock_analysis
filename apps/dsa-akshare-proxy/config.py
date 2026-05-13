# -*- coding: utf-8 -*-
"""
Akshare Proxy Service Configuration
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEBUG: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 1800  # 30 minutes

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Circuit breaker
    CB_FAILURE_THRESHOLD: int = 3
    CB_COOLDOWN_SECONDS: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
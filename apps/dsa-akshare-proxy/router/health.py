# -*- coding: utf-8 -*-
"""
Health Check Router
"""

from datetime import datetime

from fastapi import APIRouter

from models.schemas import HealthResponse
from service.cache_service import get_cache_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    cache = get_cache_service()
    redis_connected = cache.is_connected()

    return HealthResponse(
        status="healthy" if redis_connected else "degraded",
        redis_connected=redis_connected,
        timestamp=datetime.now().isoformat(),
    )
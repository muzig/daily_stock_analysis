# -*- coding: utf-8 -*-
"""
Akshare Proxy Service - FastAPI Entry Point
============================================

独立代理服务，封装 akshare 数据获取逻辑，提供统一的 REST API。
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from router import daily, realtime, health
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    logger.info(f"Akshare Proxy Service starting on {settings.HOST}:{settings.PORT}")
    logger.info(f"Redis: {settings.REDIS_URL}")
    yield
    logger.info("Akshare Proxy Service shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Akshare Proxy Service",
        description="Akshare 数据代理服务，提供股票数据获取接口",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health.router, tags=["health"])
    app.include_router(daily.router, prefix="/api/v1", tags=["daily"])
    app.include_router(realtime.router, prefix="/api/v1", tags=["realtime"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
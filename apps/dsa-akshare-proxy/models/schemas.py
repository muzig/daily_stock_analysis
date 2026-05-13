# -*- coding: utf-8 -*-
"""
Pydantic Models for Akshare Proxy API
"""

from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DailyRequest(BaseModel):
    """Request model for daily data endpoint."""
    code: str = Field(..., description="股票代码，如 '600519'")
    start_date: Optional[str] = Field(None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期 YYYY-MM-DD")
    days: int = Field(30, description="获取天数，默认30天")
    adjust: str = Field("qfq", description="复权类型：qfq=前复权，hfq=后复权，None=不复权")


class DailyResponse(BaseModel):
    """Response model for daily data."""
    code: str
    name: Optional[str] = None
    data: List[Dict[str, Any]]
    source: str = "akshare_proxy"
    cached: bool = False


class RealtimeRequest(BaseModel):
    """Request model for realtime quote endpoint."""
    code: str = Field(..., description="股票代码")


class ChipRequest(BaseModel):
    """Request model for chip distribution endpoint."""
    code: str = Field(..., description="股票代码")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    redis_connected: bool
    timestamp: str
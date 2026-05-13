# -*- coding: utf-8 -*-
"""
Daily Data Router
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models.schemas import DailyResponse
from service.akshare_service import get_akshare_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/daily", response_model=DailyResponse)
async def get_daily_data(
    code: str = Query(..., description="股票代码，如 '600519'"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    days: int = Query(30, description="获取天数，默认30天"),
    adjust: str = Query("qfq", description="复权类型：qfq=前复权，hfq=后复权"),
):
    """
    获取股票日线数据。

    支持 A 股、ETF、港股。
    """
    service = get_akshare_service()

    try:
        df, cached = service.get_daily_data(
            stock_code=code,
            start_date=start_date,
            end_date=end_date,
            days=days,
            adjust=adjust,
        )

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"未找到 {code} 的数据")

        return DailyResponse(
            code=code,
            data=df.to_dict(orient="records"),
            source="akshare_proxy",
            cached=cached,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DailyRouter] Error fetching data for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
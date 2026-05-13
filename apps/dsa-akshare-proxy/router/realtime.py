# -*- coding: utf-8 -*-
"""
Realtime Quote Router
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/realtime")
async def get_realtime_quote(
    code: str = Query(..., description="股票代码"),
):
    """
    获取股票实时行情。

    支持 A 股、ETF、港股。
    """
    # TODO: Implement realtime quote endpoint
    raise HTTPException(status_code=501, detail="Realtime endpoint not yet implemented")
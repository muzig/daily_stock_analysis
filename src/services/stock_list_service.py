# -*- coding: utf-8 -*-
"""
A 股股票列表服务

通过 akshare 获取 A 股股票列表，缓存到本地文件
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import akshare as ak
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 缓存路径
DATA_DIR = Path(__file__).parent.parent.parent / "data"
CACHE_FILE = DATA_DIR / "stock_list_a.json"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 小时


class AStockItem(BaseModel):
    """A 股股票项"""
    code: str          # 股票代码，如 "600519"
    name: str          # 股票名称，如 "贵州茅台"
    market: str        # 市场，如 "沪市主板"、"科创板"、"创业板"、"深市主板"、"北交所"
    listing_date: Optional[str] = None  # 上市日期


class AStockListResponse(BaseModel):
    """A 股列表响应"""
    stocks: List[AStockItem]
    total: int
    cached: bool
    cache_time: Optional[str] = None


def _ensure_data_dir():
    """确保数据目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_time() -> Optional[str]:
    """获取缓存时间"""
    if CACHE_FILE.exists():
        return datetime.fromtimestamp(CACHE_FILE.stat().st_mtime).isoformat()
    return None


def _is_cache_valid() -> bool:
    """检查缓存是否有效"""
    if not CACHE_FILE.exists():
        return False
    mtime = CACHE_FILE.stat().st_mtime
    return (time.time() - mtime) < CACHE_TTL_SECONDS


def _fetch_from_akshare() -> List[AStockItem]:
    """从 akshare 获取 A 股列表"""
    logger.info("[StockList] 从 akshare 获取 A 股列表...")
    stocks: List[AStockItem] = []

    try:
        # 使用 stock_zh_a_spot_em 获取沪深股票实时数据
        # 该接口获取所有沪深股票的实时行情，包含代码和名称
        df = ak.stock_zh_a_spot_em()
        logger.info(f"[StockList] 获取到 {len(df)} 条记录")

        # 字段映射 (stock_zh_a_spot_em 返回的列名)
        for _, row in df.iterrows():
            code = str(row.get("代码", "")).strip()
            name = str(row.get("名称", "")).strip()

            if not code or not name:
                continue

            # 判断市场（基于代码规则）
            market = _get_market_by_code(code)

            stocks.append(AStockItem(
                code=code,
                name=name,
                market=market,
                listing_date=None
            ))

        logger.info(f"[StockList] 解析完成，共 {len(stocks)} 只股票")
        return stocks

    except Exception as e:
        logger.error(f"[StockList] 获取失败: {e}", exc_info=True)
        raise


def _get_market_by_code(code: str) -> str:
    """根据代码判断市场"""
    code = code.strip().upper()

    # 北交所 (9开头)
    if code.startswith("9"):
        return "北交所"
    # 沪市 (6开头)
    elif code.startswith("6"):
        if code.startswith("688"):
            return "科创板"
        else:
            return "沪市主板"
    # 深市 (0、1、3开头)
    elif code.startswith("0") or code.startswith("1"):
        if code.startswith("003"):
            return "深市主板"
        elif code.startswith("001"):
            return "深市主板"
        else:
            return "深市主板"
    # 创业板 (301开头)
    elif code.startswith("301"):
        return "创业板"
    # 中小企业板 (002开头)
    elif code.startswith("2"):
        return "中小企业板"
    else:
        return "未知"


def _save_cache(stocks: List[AStockItem]):
    """保存到缓存"""
    _ensure_data_dir()
    data = {
        "stocks": [s.model_dump() for s in stocks],
        "updated_at": datetime.now().isoformat()
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"[StockList] 缓存已保存: {CACHE_FILE}")


def _load_cache() -> List[AStockItem]:
    """从缓存加载"""
    if not CACHE_FILE.exists():
        return []

    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)

        stocks = [AStockItem(**item) for item in data.get("stocks", [])]
        logger.info(f"[StockList] 从缓存加载 {len(stocks)} 只股票")
        return stocks
    except Exception as e:
        logger.warning(f"[StockList] 缓存加载失败: {e}")
        return []


def get_a_stock_list(force_refresh: bool = False) -> AStockListResponse:
    """
    获取 A 股列表

    Args:
        force_refresh: 是否强制刷新缓存

    Returns:
        AStockListResponse
    """
    # 检查缓存
    if not force_refresh and _is_cache_valid():
        stocks = _load_cache()
        return AStockListResponse(
            stocks=stocks,
            total=len(stocks),
            cached=True,
            cache_time=_get_cache_time()
        )

    # 获取新数据
    stocks = _fetch_from_akshare()

    # 保存缓存
    _save_cache(stocks)

    return AStockListResponse(
        stocks=stocks,
        total=len(stocks),
        cached=False,
        cache_time=datetime.now().isoformat()
    )


def get_a_stock_list_by_market(market: Optional[str] = None) -> AStockListResponse:
    """按市场筛选获取 A 股列表"""
    response = get_a_stock_list()

    if market:
        filtered = [s for s in response.stocks if s.market == market]
        response.stocks = filtered
        response.total = len(filtered)

    return response

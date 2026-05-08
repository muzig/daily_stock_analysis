# -*- coding: utf-8 -*-
"""
股票列表服务

通过 akshare 获取 A 股、ETF 列表，缓存到本地文件
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import akshare as ak
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 缓存路径
DATA_DIR = Path(__file__).parent.parent.parent / "data"
STOCK_CACHE_FILE = DATA_DIR / "stock_list_a.json"
ETF_CACHE_FILE = DATA_DIR / "stock_list_etf.json"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 小时


class AStockItem(BaseModel):
    """A 股股票项"""
    code: str          # 股票代码，如 "600519"
    name: str          # 股票名称，如 "贵州茅台"
    market: str        # 市场，如 "沪市主板"、"科创板"、"创业板"、"深市主板"、"北交所"
    industry: Optional[str] = None  # 行业
    listing_date: Optional[str] = None  # 上市日期


class ETFItem(BaseModel):
    """ETF 项"""
    code: str          # ETF 代码，如 "510300"
    name: str          # ETF 名称，如 "沪深300ETF"
    market: str        # 市场
    type: str         # 类型，如 "股票指数"、"债券"、"商品"等


class AStockListResponse(BaseModel):
    """A 股列表响应"""
    stocks: List[AStockItem]
    total: int
    cached: bool
    cache_time: Optional[str] = None


class ETFListResponse(BaseModel):
    """ETF 列表响应"""
    etfs: List[ETFItem]
    total: int
    cached: bool
    cache_time: Optional[str] = None


class IndustryItem(BaseModel):
    """行业项"""
    name: str
    code: str
    stock_count: int = 0


class IndustryListResponse(BaseModel):
    """行业列表响应"""
    industries: List[IndustryItem]
    total: int


def _ensure_data_dir():
    """确保数据目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_time(cache_file: Path) -> Optional[str]:
    """获取缓存时间"""
    if cache_file.exists():
        return datetime.fromtimestamp(cache_file.stat().st_mtime).isoformat()
    return None


def _is_cache_valid(cache_file: Path) -> bool:
    """检查缓存是否有效"""
    if not cache_file.exists():
        return False
    mtime = cache_file.stat().st_mtime
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


def _save_stock_cache(stocks: List[AStockItem]):
    """保存 A 股到缓存"""
    _ensure_data_dir()
    data = {
        "stocks": [s.model_dump() for s in stocks],
        "updated_at": datetime.now().isoformat()
    }
    with open(STOCK_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"[StockList] A股缓存已保存: {STOCK_CACHE_FILE}")


def _load_stock_cache() -> List[AStockItem]:
    """从缓存加载 A 股"""
    if not STOCK_CACHE_FILE.exists():
        return []

    try:
        with open(STOCK_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)

        stocks = [AStockItem(**item) for item in data.get("stocks", [])]
        logger.info(f"[StockList] 从缓存加载 {len(stocks)} 只A股")
        return stocks
    except Exception as e:
        logger.warning(f"[StockList] A股缓存加载失败: {e}")
        return []


def _save_etf_cache(etfs: List[ETFItem]):
    """保存 ETF 到缓存"""
    _ensure_data_dir()
    data = {
        "etfs": [e.model_dump() for e in etfs],
        "updated_at": datetime.now().isoformat()
    }
    with open(ETF_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"[StockList] ETF缓存已保存: {ETF_CACHE_FILE}")


def _load_etf_cache() -> List[ETFItem]:
    """从缓存加载 ETF"""
    if not ETF_CACHE_FILE.exists():
        return []

    try:
        with open(ETF_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)

        etfs = [ETFItem(**item) for item in data.get("etfs", [])]
        logger.info(f"[StockList] 从缓存加载 {len(etfs)} 只ETF")
        return etfs
    except Exception as e:
        logger.warning(f"[StockList] ETF缓存加载失败: {e}")
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
    if not force_refresh and _is_cache_valid(STOCK_CACHE_FILE):
        stocks = _load_stock_cache()
        return AStockListResponse(
            stocks=stocks,
            total=len(stocks),
            cached=True,
            cache_time=_get_cache_time(STOCK_CACHE_FILE)
        )

    # 获取新数据
    stocks = _fetch_from_akshare()

    # 保存缓存
    _save_stock_cache(stocks)

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


def get_industry_list() -> IndustryListResponse:
    """
    获取行业列表

    Returns:
        IndustryListResponse
    """
    try:
        logger.info("[StockList] 获取行业列表...")
        df = ak.stock_board_industry_name_em()
        logger.info(f"[StockList] 获取到 {len(df)} 个行业")

        industries = []
        for _, row in df.iterrows():
            industries.append(IndustryItem(
                name=str(row.get("板块名称", "")).strip(),
                code=str(row.get("板块代码", "")).strip(),
                stock_count=int(row.get("上涨家数", 0)) + int(row.get("下跌家数", 0))
            ))

        # 按股票数量降序排列
        industries.sort(key=lambda x: x.stock_count, reverse=True)

        return IndustryListResponse(
            industries=industries,
            total=len(industries)
        )
    except Exception as e:
        logger.error(f"[StockList] 获取行业列表失败: {e}", exc_info=True)
        raise


def get_stocks_by_industry(industry_code: str) -> AStockListResponse:
    """
    获取指定行业的成分股

    Args:
        industry_code: 行业板块代码

    Returns:
        AStockListResponse
    """
    try:
        logger.info(f"[StockList] 获取行业 {industry_code} 的成分股...")
        df = ak.stock_board_industry_cons_em(symbol=industry_code)
        logger.info(f"[StockList] 获取到 {len(df)} 只成分股")

        stocks = []
        for _, row in df.iterrows():
            code = str(row.get("代码", "")).strip()
            name = str(row.get("名称", "")).strip()

            if not code or not name:
                continue

            stocks.append(AStockItem(
                code=code,
                name=name,
                market=_get_market_by_code(code),
                industry=None  # 成分股数据不含行业字段
            ))

        return AStockListResponse(
            stocks=stocks,
            total=len(stocks),
            cached=False
        )
    except Exception as e:
        logger.error(f"[StockList] 获取行业成分股失败: {e}", exc_info=True)
        raise


def _get_etf_type_by_code(code: str) -> str:
    """根据 ETF 代码判断类型"""
    # ETF 代码规则：51xxx - 股票指数, 15xxx - 债券, 51xxx/13xxx - 货币, 20xxx - LOF等
    code = code.strip().upper()
    if code.startswith("51"):
        return "股票指数"
    elif code.startswith("15"):
        return "债券"
    elif code.startswith("13") or code.startswith("51"):
        return "货币"
    elif code.startswith("20"):
        return "LOF"
    elif code.startswith("16"):
        return "商品"
    elif code.startswith("17"):
        return "黄金"
    else:
        return "其他"


def _fetch_etf_from_akshare() -> List[ETFItem]:
    """从 akshare 获取 ETF 列表"""
    logger.info("[StockList] 从 akshare 获取 ETF 列表...")
    etfs: List[ETFItem] = []

    try:
        # 获取 ETF 列表
        df = ak.fund_etf_spot_em()
        logger.info(f"[StockList] 获取到 {len(df)} 条 ETF 记录")

        for _, row in df.iterrows():
            code = str(row.get("代码", "")).strip()
            name = str(row.get("名称", "")).strip()

            if not code or not name:
                continue

            etfs.append(ETFItem(
                code=code,
                name=name,
                market="交易所",
                type=_get_etf_type_by_code(code)
            ))

        logger.info(f"[StockList] ETF 解析完成，共 {len(etfs)} 只")
        return etfs

    except Exception as e:
        logger.error(f"[StockList] 获取 ETF 列表失败: {e}", exc_info=True)
        raise


def get_etf_list(force_refresh: bool = False) -> ETFListResponse:
    """
    获取 ETF 列表

    Args:
        force_refresh: 是否强制刷新缓存

    Returns:
        ETFListResponse
    """
    # 检查缓存
    if not force_refresh and _is_cache_valid(ETF_CACHE_FILE):
        etfs = _load_etf_cache()
        return ETFListResponse(
            etfs=etfs,
            total=len(etfs),
            cached=True,
            cache_time=_get_cache_time(ETF_CACHE_FILE)
        )

    # 获取新数据
    etfs = _fetch_etf_from_akshare()

    # 保存缓存
    _save_etf_cache(etfs)

    return ETFListResponse(
        etfs=etfs,
        total=len(etfs),
        cached=False,
        cache_time=datetime.now().isoformat()
    )


def get_etf_industry_list() -> IndustryListResponse:
    """
    获取 ETF 行业/类型列表

    Returns:
        IndustryListResponse
    """
    # ETF 按类型分类
    response = get_etf_list()
    type_count: Dict[str, int] = {}
    for etf in response.etfs:
        t = etf.type
        type_count[t] = type_count.get(t, 0) + 1

    industries = [
        IndustryItem(name=name, code=code, stock_count=count)
        for name, (code, count) in {
            "股票指数": ("stock", type_count.get("股票指数", 0)),
            "债券": ("bond", type_count.get("债券", 0)),
            "货币": ("money", type_count.get("货币", 0)),
            "LOF": ("lof", type_count.get("LOF", 0)),
            "商品": ("commodity", type_count.get("商品", 0)),
            "黄金": ("gold", type_count.get("黄金", 0)),
            "其他": ("other", type_count.get("其他", 0)),
        }.items()
        if count > 0
    ]
    industries.sort(key=lambda x: x.stock_count, reverse=True)

    return IndustryListResponse(
        industries=industries,
        total=len(industries)
    )


def get_etfs_by_type(etf_type: str) -> ETFListResponse:
    """
    获取指定类型的 ETF

    Args:
        etf_type: ETF 类型

    Returns:
        ETFListResponse
    """
    response = get_etf_list()

    if etf_type:
        filtered = [e for e in response.etfs if e.type == etf_type]
        response.etfs = filtered
        response.total = len(filtered)

    return response

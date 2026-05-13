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
STALE_CACHE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 过期缓存最大保留 7 天
MAX_RETRIES = 3  # 最大重试次数

# 前端静态索引文件路径（用于兜底）
# 使用 apps/dsa-web/public/ 而非 static/，因为 static/ 在构建时生成且被 gitignore
FRONTEND_INDEX_FILE = Path(__file__).parent.parent.parent / "apps" / "dsa-web" / "public" / "stocks.index.json"


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


def _is_stale_cache_valid(cache_file: Path) -> bool:
    """检查过期缓存是否可用（过期时间在允许范围内）"""
    if not cache_file.exists():
        return False
    mtime = cache_file.stat().st_mtime
    age = time.time() - mtime
    return age < STALE_CACHE_MAX_AGE_SECONDS


def _fetch_from_akshare() -> List[AStockItem]:
    """从 akshare 获取 A 股列表，带重试机制"""
    logger.info("[StockList] 从 akshare 获取 A 股列表...")
    stocks: List[AStockItem] = []

    last_error = None
    for attempt in range(MAX_RETRIES):
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
            last_error = e
            logger.warning(f"[StockList] 获取失败（第 {attempt + 1}/{MAX_RETRIES} 次）: {e}")
            if attempt < MAX_RETRIES - 1:
                # 指数退避: 2, 4, 8 秒
                wait_time = 2 ** (attempt + 1)
                logger.info(f"[StockList] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

    # 所有重试都失败了
    logger.error(f"[StockList] 获取失败，已重试 {MAX_RETRIES} 次: {last_error}")
    raise last_error


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


def _load_frontend_index_fallback() -> List[AStockItem]:
    """从前端静态索引文件兜底加载 A 股列表"""
    if not FRONTEND_INDEX_FILE.exists():
        logger.warning(f"[StockList] 前端索引文件不存在: {FRONTEND_INDEX_FILE}")
        return []

    try:
        with open(FRONTEND_INDEX_FILE, encoding="utf-8") as f:
            data = json.load(f)

        stocks = []
        for item in data:
            # 格式: ["000001.SZ","000001","平安银行","pinganyinhang","payh",["平银"],"CN","stock",true,100]
            if not isinstance(item, list) or len(item) < 3:
                continue
            code = str(item[1]).strip()  # display_code 如 "000001"
            name = str(item[2]).strip()  # name_zh 如 "平安银行"
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

        logger.info(f"[StockList] 从前端索引加载 {len(stocks)} 只股票")
        return stocks
    except Exception as e:
        logger.warning(f"[StockList] 前端索引加载失败: {e}")
        return []


def get_a_stock_list(force_refresh: bool = False) -> AStockListResponse:
    """
    获取 A 股列表

    Args:
        force_refresh: 是否强制刷新缓存

    Returns:
        AStockListResponse
    """
    # 默认优先使用本地缓存，不走网络
    if not force_refresh:
        if _is_cache_valid(STOCK_CACHE_FILE):
            stocks = _load_stock_cache()
            return AStockListResponse(
                stocks=stocks,
                total=len(stocks),
                cached=True,
                cache_time=_get_cache_time(STOCK_CACHE_FILE)
            )
        # 缓存无效或不存在，使用前端静态索引兜底
        stocks = _load_frontend_index_fallback()
        if stocks:
            logger.info(f"[StockList] 使用前端索引返回 {len(stocks)} 只股票")
            return AStockListResponse(
                stocks=stocks,
                total=len(stocks),
                cached=True,
                cache_time=None
            )

    # force_refresh 时尝试从 akshare 获取
    try:
        stocks = _fetch_from_akshare()
        _save_stock_cache(stocks)
        return AStockListResponse(
            stocks=stocks,
            total=len(stocks),
            cached=False,
            cache_time=datetime.now().isoformat()
        )
    except Exception as e:
        # akshare 失败，降级到过期缓存
        logger.warning(f"[StockList] 网络获取失败，尝试使用过期缓存: {e}")
        if _is_stale_cache_valid(STOCK_CACHE_FILE):
            stocks = _load_stock_cache()
            if stocks:
                logger.info(f"[StockList] 使用过期缓存返回 {len(stocks)} 只股票")
                return AStockListResponse(
                    stocks=stocks,
                    total=len(stocks),
                    cached=True,
                    cache_time=_get_cache_time(STOCK_CACHE_FILE)
                )
        # 过期缓存也没有，使用前端索引
        stocks = _load_frontend_index_fallback()
        if stocks:
            logger.info(f"[StockList] 使用前端索引兜底返回 {len(stocks)} 只股票")
            return AStockListResponse(
                stocks=stocks,
                total=len(stocks),
                cached=True,
                cache_time=None
            )
        raise


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
        # 网络失败时返回空列表，不阻断股票列表展示
        return IndustryListResponse(industries=[], total=0)


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


# ETF 名称关键词 → 行业分类映射表（按优先级排序，长关键词在前避免误匹配）
_ETF_TYPE_KEYWORDS: list[tuple[str, str]] = [
    # 债券类（资产大类优先）
    ("可转债", "债券"), ("信用债", "债券"), ("城投债", "债券"),
    ("政金债", "债券"), ("国债", "债券"), ("转债", "债券"),
    ("地债", "债券"), ("债券", "债券"),
    # 货币类
    ("保证金", "货币"), ("理财", "货币"), ("现金", "货币"), ("货币", "货币"),
    # 黄金
    ("上海金", "黄金"), ("金ETF", "黄金"), ("黄金", "黄金"),
    # 跨境（港股通必须在港股之前）
    ("港股通", "跨境"), ("纳斯达克", "跨境"), ("道琼斯", "跨境"),
    ("日经", "跨境"), ("德国", "跨境"), ("法国", "跨境"),
    ("印度", "跨境"), ("越南", "跨境"), ("恒生", "跨境"),
    ("港股", "跨境"), ("中概", "跨境"), ("标普", "跨境"),
    # === 行业主题（优先于宽基，避免"创业板新能源"被错分为宽基）===
    # 科技
    ("人工智能", "科技"), ("云计算", "科技"), ("物联网", "科技"),
    ("机器人", "科技"), ("半导体", "科技"), ("大数据", "科技"),
    ("计算机", "科技"), ("芯片", "科技"), ("通信", "科技"),
    ("AI", "科技"), ("5G", "科技"), ("电子", "科技"), ("软件", "科技"),
    # 医药（"创新药"在"医药"前）
    ("创新药", "医药"), ("医械", "医药"), ("疫苗", "医药"),
    ("医药", "医药"), ("医疗", "医药"), ("生物", "医药"), ("中药", "医药"),
    # 新能源（"新能源"在"能源"前）
    ("新能源汽车", "新能源"), ("新能源车", "新能源"), ("新能源", "新能源"),
    ("碳中和", "新能源"), ("光伏", "新能源"), ("锂电", "新能源"),
    ("风电", "新能源"), ("储能", "新能源"), ("电池", "新能源"),
    ("环保", "新能源"), ("绿色", "新能源"),
    # 军工
    ("航空航天", "军工"), ("军工", "军工"), ("国防", "军工"),
    # 消费
    ("白酒", "消费"), ("食品", "消费"), ("饮料", "消费"),
    ("农牧", "消费"), ("养殖", "消费"), ("农业", "消费"),
    ("家电", "消费"), ("汽车", "消费"), ("旅游", "消费"),
    ("消费", "消费"), ("酒", "消费"),
    # 金融
    ("房地产", "金融"), ("证券", "金融"), ("券商", "金融"),
    ("银行", "金融"), ("保险", "金融"), ("地产", "金融"),
    ("金融", "金融"),
    # 传媒
    ("传媒", "传媒"), ("游戏", "传媒"), ("影视", "传媒"),
    ("娱乐", "传媒"), ("教育", "传媒"),
    # 基建红利
    ("一带一路", "基建红利"), ("高股息", "基建红利"),
    ("基建", "基建红利"), ("高铁", "基建红利"),
    ("央企", "基建红利"), ("国企", "基建红利"),
    ("红利", "基建红利"), ("股息", "基建红利"),
    # === 商品（在行业主题之后，避免"能源"错误匹配"新能源"）===
    ("农产品", "商品"), ("豆粕", "商品"), ("原油", "商品"),
    ("白银", "商品"), ("有色", "商品"), ("能源", "商品"),
    ("化工", "商品"), ("煤炭", "商品"), ("钢铁", "商品"),
    ("资源", "商品"), ("商品", "商品"),
    # === 宽基指数（最后匹配，最通用）===
    ("沪深300", "宽基"), ("中证2000", "宽基"), ("中证1000", "宽基"),
    ("中证500", "宽基"), ("中证A50", "宽基"), ("上证180", "宽基"),
    ("上证指数", "宽基"), ("深证100", "宽基"), ("科创100", "宽基"),
    ("科创50", "宽基"), ("上证50", "宽基"), ("中证A", "宽基"),
    ("创业板", "宽基"), ("上证", "宽基"), ("深证", "宽基"),
    ("科创", "宽基"), ("中证", "宽基"), ("沪深", "宽基"),
    ("A50", "宽基"),
    # "电力" 放在最后单独处理 —— 如果没被"新能源"匹配，归入"新能源"更合理
    ("电力", "新能源"),
]

def _get_etf_type_by_name(name: str) -> str:
    """根据 ETF 名称关键词判断行业类型"""
    for keyword, category in _ETF_TYPE_KEYWORDS:
        if keyword in name:
            return category
    return "其他"


def _fetch_etf_from_akshare() -> List[ETFItem]:
    """从 akshare 获取 ETF 列表，带重试机制"""
    logger.info("[StockList] 从 akshare 获取 ETF 列表...")
    etfs: List[ETFItem] = []

    last_error = None
    for attempt in range(MAX_RETRIES):
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
                    type=_get_etf_type_by_name(name)
                ))

            logger.info(f"[StockList] ETF 解析完成，共 {len(etfs)} 只")
            return etfs

        except Exception as e:
            last_error = e
            logger.warning(f"[StockList] 获取 ETF 失败（第 {attempt + 1}/{MAX_RETRIES} 次）: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = 2 ** (attempt + 1)
                logger.info(f"[StockList] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

    logger.error(f"[StockList] 获取 ETF 失败，已重试 {MAX_RETRIES} 次: {last_error}")
    raise last_error


# ETF 兜底索引文件路径（优先使用前端 public 目录，备选使用 data 目录）
ETF_FALLBACK_FILE = Path(__file__).parent.parent.parent / "apps" / "dsa-web" / "public" / "etf.index.json"
ETF_CACHE_FALLBACK_FILE = DATA_DIR / "stock_list_etf.json"


def _load_etf_fallback() -> List[ETFItem]:
    """从缓存文件加载 ETF 列表作为兜底"""
    # 优先从前端 public 目录读取
    fallback_file = ETF_FALLBACK_FILE
    if not fallback_file.exists():
        fallback_file = ETF_CACHE_FALLBACK_FILE

    if not fallback_file.exists():
        return []
    try:
        with open(fallback_file, encoding="utf-8") as f:
            data = json.load(f)
        etfs = [ETFItem(**item) for item in data.get("etfs", [])]
        logger.info(f"[StockList] 从 ETF 兜底文件加载 {len(etfs)} 只 ETF: {fallback_file}")
        return etfs
    except Exception as e:
        logger.warning(f"[StockList] ETF 兜底文件加载失败: {e}")
        return []


def get_etf_list(force_refresh: bool = False) -> ETFListResponse:
    """
    获取 ETF 列表

    Args:
        force_refresh: 是否强制刷新缓存

    Returns:
        ETFListResponse
    """
    # 默认优先使用本地缓存，不走网络
    if not force_refresh:
        if _is_cache_valid(ETF_CACHE_FILE):
            etfs = _load_etf_cache()
            return ETFListResponse(
                etfs=etfs,
                total=len(etfs),
                cached=True,
                cache_time=_get_cache_time(ETF_CACHE_FILE)
            )
        # 缓存无效或不存在，使用 ETF 缓存文件兜底
        etfs = _load_etf_fallback()
        if etfs:
            logger.info(f"[StockList] 使用 ETF 缓存文件返回 {len(etfs)} 只 ETF")
            return ETFListResponse(
                etfs=etfs,
                total=len(etfs),
                cached=True,
                cache_time=None
            )

    # force_refresh 时尝试从 akshare 获取
    try:
        etfs = _fetch_etf_from_akshare()
        _save_etf_cache(etfs)
        return ETFListResponse(
            etfs=etfs,
            total=len(etfs),
            cached=False,
            cache_time=datetime.now().isoformat()
        )
    except Exception as e:
        # 网络失败，降级到过期缓存
        logger.warning(f"[StockList] ETF 网络获取失败，尝试使用过期缓存: {e}")
        if _is_stale_cache_valid(ETF_CACHE_FILE):
            etfs = _load_etf_cache()
            if etfs:
                logger.info(f"[StockList] 使用过期缓存返回 {len(etfs)} 只 ETF")
                return ETFListResponse(
                    etfs=etfs,
                    total=len(etfs),
                    cached=True,
                    cache_time=_get_cache_time(ETF_CACHE_FILE)
                )
        # 过期缓存也没有，使用 ETF 缓存文件兜底
        etfs = _load_etf_fallback()
        if etfs:
            logger.info(f"[StockList] 使用 ETF 缓存文件兜底返回 {len(etfs)} 只 ETF")
            return ETFListResponse(
                etfs=etfs,
                total=len(etfs),
                cached=True,
                cache_time=None
            )
        # 没有可用缓存，返回空列表
        logger.warning(f"[StockList] ETF 无可用缓存，返回空列表")
        return ETFListResponse(etfs=[], total=0, cached=True, cache_time=None)


def get_etf_industry_list() -> IndustryListResponse:
    """
    获取 ETF 行业/类型列表

    Returns:
        IndustryListResponse
    """
    # ETF 按名称关键词分类统计
    response = get_etf_list()
    type_count: dict[str, int] = {}
    for etf in response.etfs:
        t = etf.type
        type_count[t] = type_count.get(t, 0) + 1

    # 按预设顺序构建行业列表
    category_order = ["宽基", "科技", "医药", "新能源", "金融", "消费",
                      "军工", "传媒", "基建红利", "跨境", "债券", "商品",
                      "黄金", "货币", "其他"]
    industries = []
    for cat in category_order:
        count = type_count.get(cat, 0)
        if count > 0:
            industries.append(IndustryItem(name=cat, code=cat, stock_count=count))

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

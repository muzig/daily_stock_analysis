/**
 * StockListPage
 *
 * A-share stock list and ETF list page - Left category + Right grid layout with favorites section
 */

import { useCallback, useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAStockList, useIndustryList, useETFList, type AStockItem, type IndustryItem, type ETFItem } from '../hooks/useAStockList';
import { useFavorites } from '../hooks';

const MARKET_LABELS: Record<string, string> = {
  "沪市主板": "沪市",
  "科创板": "科创",
  "中小企业板": "中小",
  "创业板": "创业",
  "深市主板": "深市",
  "北交所": "北交所",
  "沪市其他": "沪市",
  "未知": "未知",
};

const MARKET_COLORS: Record<string, string> = {
  "科创板": 'dark:bg-purple-500/25 dark:text-purple-300 dark:border-purple-500/40 dark:shadow-[0_0_12px_rgba(168,85,247,0.15)] bg-purple-100 text-purple-700 border-purple-300/50',
  "创业板": 'dark:bg-blue-500/25 dark:text-blue-300 dark:border-blue-500/40 dark:shadow-[0_0_12px_rgba(59,130,246,0.15)] bg-blue-100 text-blue-700 border-blue-300/50',
  "北交所": 'dark:bg-amber-500/25 dark:text-amber-300 dark:border-amber-500/40 dark:shadow-[0_0_12px_rgba(245,158,11,0.15)] bg-amber-100 text-amber-700 border-amber-300/50',
  "沪市主板": 'dark:bg-slate-500/25 dark:text-slate-300 dark:border-slate-500/40 dark:shadow-[0_0_12px_rgba(100,116,139,0.12)] bg-slate-200 text-slate-600 border-slate-300/50',
  "中小企业板": 'dark:bg-emerald-500/25 dark:text-emerald-300 dark:border-emerald-500/40 dark:shadow-[0_0_12px_rgba(16,185,129,0.15)] bg-emerald-100 text-emerald-700 border-emerald-300/50',
  "深市主板": 'dark:bg-cyan-500/25 dark:text-cyan-300 dark:border-cyan-500/40 dark:shadow-[0_0_12px_rgba(6,182,212,0.15)] bg-cyan-100 text-cyan-700 border-cyan-300/50',
};

interface IndustryGroup {
  industry: IndustryItem;
  stocks: (AStockItem | ETFItem)[];
}

function groupStocksByIndustry(stocks: AStockItem[], _industries: IndustryItem[], starredCodes: string[]): IndustryGroup[] {
  if (stocks.length === 0) return [];

  const sorted = [...stocks].sort((a, b) => {
    const aStarred = starredCodes.includes(a.code);
    const bStarred = starredCodes.includes(b.code);
    if (aStarred && !bStarred) return -1;
    if (!aStarred && bStarred) return 1;
    return a.code.localeCompare(b.code);
  });

  return [{
    industry: { name: '全行业', code: 'all', stock_count: sorted.length },
    stocks: sorted,
  }];
}

interface ETFCategoryItem {
  type: string;
  count: number;
}

const StockCard: React.FC<{
  stock: AStockItem;
  starred: boolean;
  onToggleFavorite: (code: string) => void;
  onStockClick: (code: string, name: string) => void;
  index: number;
}> = ({ stock, starred, onToggleFavorite, onStockClick, index }) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), index * 15);
    return () => clearTimeout(timer);
  }, [index]);

  const marketClass = MARKET_COLORS[stock.market] || 'dark:bg-slate-500/25 dark:text-slate-300 dark:border-slate-500/40 dark:shadow-[0_0_12px_rgba(100,116,139,0.12)] bg-slate-200 text-slate-600 border-slate-300/50';

  return (
    <div
      className={`transition-all duration-300 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}`}
    >
      <div
        onClick={() => onStockClick(stock.code, stock.name)}
        className="group relative dark:bg-slate-800/95 dark:border-slate-700/80 dark:hover:border-cyan-500/40 dark:hover:bg-slate-800 dark:hover:shadow-lg dark:hover:shadow-cyan-500/5 bg-white border-slate-200 hover:border-cyan-400/50 hover:bg-white hover:shadow-md hover:shadow-cyan-500/10 rounded-xl p-3 cursor-pointer transition-all duration-200"
      >
        <button
          onClick={(e) => { e.stopPropagation(); onToggleFavorite(stock.code); }}
          className={`absolute top-2 right-2 text-lg hover:scale-110 transition-transform ${starred ? 'text-amber-400' : 'dark:text-slate-500 text-slate-400 hover:text-amber-400'}`}
        >
          {starred ? '★' : '☆'}
        </button>

        <div className="font-mono text-xs dark:text-slate-400 text-slate-500 mb-1.5">{stock.code}</div>

        <div className="font-medium text-sm dark:text-gray-100 text-slate-800 mb-2 group-hover:text-cyan-500 dark:group-hover:text-cyan-400 transition-colors truncate pr-5">
          {stock.name}
        </div>

        <span className={`inline-block rounded px-1.5 py-0.5 text-xs ${marketClass}`}>
          {MARKET_LABELS[stock.market] || stock.market}
        </span>
      </div>
    </div>
  );
};

const ETFCard: React.FC<{
  etf: ETFItem;
  starred: boolean;
  onToggleFavorite: (code: string) => void;
  onStockClick: (code: string, name: string) => void;
  index: number;
}> = ({ etf, starred, onToggleFavorite, onStockClick, index }) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), index * 15);
    return () => clearTimeout(timer);
  }, [index]);

  return (
    <div
      className={`transition-all duration-300 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}`}
    >
      <div
        onClick={() => onStockClick(etf.code, etf.name)}
        className="group relative dark:bg-slate-800/95 dark:border-slate-700/80 dark:hover:border-cyan-500/40 dark:hover:bg-slate-800 dark:hover:shadow-lg dark:hover:shadow-cyan-500/5 bg-white border-slate-200 hover:border-cyan-400/50 hover:bg-white hover:shadow-md hover:shadow-cyan-500/10 rounded-xl p-3 cursor-pointer transition-all duration-200"
      >
        <button
          onClick={(e) => { e.stopPropagation(); onToggleFavorite(etf.code); }}
          className={`absolute top-2 right-2 text-lg hover:scale-110 transition-transform ${starred ? 'text-amber-400' : 'dark:text-slate-500 text-slate-400 hover:text-amber-400'}`}
        >
          {starred ? '★' : '☆'}
        </button>

        <div className="font-mono text-xs dark:text-slate-400 text-slate-500 mb-1.5">{etf.code}</div>

        <div className="font-medium text-sm dark:text-gray-100 text-slate-800 mb-2 group-hover:text-cyan-500 dark:group-hover:text-cyan-400 transition-colors truncate pr-5">
          {etf.name}
        </div>

        <span className="inline-block rounded px-1.5 py-0.5 text-xs dark:bg-emerald-500/25 dark:text-emerald-300 dark:border dark:border-emerald-500/40 dark:shadow-[0_0_12px_rgba(16,185,129,0.15)] bg-emerald-100 text-emerald-700 border-emerald-300/50">
          {etf.type}
        </span>
      </div>
    </div>
  );
};

const FavoritesSection: React.FC<{
  items: (AStockItem | ETFItem)[];
  favorites: string[];
  onToggleFavorite: (code: string) => void;
  onStockClick: (code: string, name: string) => void;
  type: 'stock' | 'etf';
}> = ({ items, favorites, onToggleFavorite, onStockClick, type }) => {
  const starredItems = useMemo(() => {
    return items.filter(item => favorites.includes(item.code));
  }, [items, favorites]);

  if (starredItems.length === 0) return null;

  return (
    <div className="px-3 sm:px-6 py-3 sm:py-4 dark:border-slate-800/80 border-slate-200/60 dark:bg-slate-900/30 bg-slate-50/50">
      <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
        <span className="text-amber-400 text-sm sm:text-lg">★</span>
        <h2 className="text-xs sm:text-sm font-medium dark:text-gray-200 text-slate-700">我的收藏</h2>
        <span className="text-xs dark:text-slate-500 text-slate-400">({starredItems.length})</span>
      </div>
      <div className="flex gap-2 sm:gap-3 overflow-x-auto pb-2">
        {starredItems.map((item, index) => (
          <div key={item.code} className="flex-shrink-0 w-32 sm:w-36">
            {type === 'stock' ? (
              <StockCard
                stock={item as AStockItem}
                starred={true}
                onToggleFavorite={onToggleFavorite}
                onStockClick={onStockClick}
                index={index}
              />
            ) : (
              <ETFCard
                etf={item as ETFItem}
                starred={true}
                onToggleFavorite={onToggleFavorite}
                onStockClick={onStockClick}
                index={index}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const CategoryNav: React.FC<{
  categories: ETFCategoryItem[];
  selectedType: string | null;
  onSelect: (type: string | null) => void;
  collapsed?: boolean;
}> = ({ categories, selectedType, onSelect, collapsed = false }) => {
  return (
    <nav className={`flex-shrink-0 dark:border-slate-700/50 border-slate-200/60 dark:bg-slate-900/50 bg-slate-100/60 overflow-y-auto transition-all duration-300 ease-in-out ${collapsed ? 'w-0 opacity-0 pointer-events-none' : 'w-32 sm:w-36 md:w-40 lg:w-48 opacity-100'}`}>
      {!collapsed && (
        <div className="p-3 sm:p-4 h-full">
          <h2 className="text-xs font-medium dark:text-slate-400 text-slate-500 uppercase tracking-wider mb-2 sm:mb-3">ETF 类型</h2>
          <div className="space-y-0.5 sm:space-y-1">
            <button
              onClick={() => onSelect(null)}
              className={`w-full text-left px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-xs sm:text-sm transition-all ${
                selectedType === null
                  ? 'dark:bg-cyan-500/15 dark:text-cyan-400 dark:border-cyan-500/30 bg-cyan-100/80 text-cyan-700 border-cyan-300/50'
                  : 'dark:text-slate-400 text-slate-500 dark:hover:bg-slate-800/60 dark:hover:text-gray-200 hover:bg-slate-200/70 hover:text-slate-700'
              }`}
            >
              <span className="flex items-center justify-between">
                <span>全部</span>
                <span className="text-xs dark:text-slate-500 text-slate-400">{categories.reduce((s, c) => s + c.count, 0)}</span>
              </span>
            </button>
            {categories.map((cat) => (
              <button
                key={cat.type}
                onClick={() => onSelect(cat.type)}
                className={`w-full text-left px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-xs sm:text-sm transition-all ${
                  selectedType === cat.type
                    ? 'dark:bg-cyan-500/15 dark:text-cyan-400 dark:border-cyan-500/30 bg-cyan-100/80 text-cyan-700 border-cyan-300/50'
                    : 'dark:text-slate-400 text-slate-500 dark:hover:bg-slate-800/60 dark:hover:text-gray-200 hover:bg-slate-200/70 hover:text-slate-700'
                }`}
              >
                <span className="flex items-center justify-between">
                  <span className="truncate">{cat.type}</span>
                  <span className="text-xs dark:text-slate-500 text-slate-400">{cat.count}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
};

const ETFGrid: React.FC<{
  etfs: ETFItem[];
  favorites: string[];
  onToggleFavorite: (code: string) => void;
  onStockClick: (code: string, name: string) => void;
}> = ({ etfs, favorites, onToggleFavorite, onStockClick }) => {
  // Separate favorites from non-favorites
  const { starred, others } = useMemo(() => {
    const starred: ETFItem[] = [];
    const others: ETFItem[] = [];
    etfs.forEach(etf => {
      if (favorites.includes(etf.code)) {
        starred.push(etf);
      } else {
        others.push(etf);
      }
    });
    return { starred, others };
  }, [etfs, favorites]);

  if (etfs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        <div className="text-center">
          <div className="text-4xl mb-3 opacity-30">📭</div>
          <p>该分类下暂无 ETF</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Favorites row at top */}
      {starred.length > 0 && (
        <div className="px-3 sm:px-6 py-3 sm:py-4 dark:border-slate-800/80 border-slate-200/60 dark:bg-slate-900/20 bg-slate-50/40">
          <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
            <span className="text-amber-400 text-sm sm:text-lg">★</span>
            <h2 className="text-xs sm:text-sm font-medium dark:text-gray-200 text-slate-700">我的收藏</h2>
            <span className="text-xs dark:text-slate-500 text-slate-400">({starred.length})</span>
          </div>
          <div className="flex gap-2 sm:gap-3 overflow-x-auto pb-2">
            {starred.map((etf, index) => (
              <div key={etf.code} className="flex-shrink-0 w-32 sm:w-36">
                <ETFCard
                  etf={etf}
                  starred={true}
                  onToggleFavorite={onToggleFavorite}
                  onStockClick={onStockClick}
                  index={index}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Non-favorite items grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-2 sm:gap-3 p-3 sm:p-6">
        {others.map((etf, index) => (
          <ETFCard
            key={etf.code}
            etf={etf}
            starred={false}
            onToggleFavorite={onToggleFavorite}
            onStockClick={onStockClick}
            index={index + starred.length}
          />
        ))}
      </div>
    </>
  );
};

const StockListPage: React.FC = () => {
  const navigate = useNavigate();
  const [listType, setListType] = useState<'stock' | 'etf'>(() => {
    const saved = localStorage.getItem('stockList_type');
    return (saved === 'stock' || saved === 'etf') ? saved : 'stock';
  });
  const [stockEnabled] = useState(true);
  const [etfEnabled] = useState(true);
  const [selectedETFType, setSelectedETFType] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const { stocks, loading, error, cached, refresh } = useAStockList({ enabled: stockEnabled });
  const { industries } = useIndustryList();
  const { etfs, loading: etfLoading, cached: etfCached, refresh: etfRefresh } = useETFList({ enabled: etfEnabled });
  const { favorites, toggleFavorite } = useFavorites(listType);

  const stockReady = stockEnabled && !loading;
  const etfReady = etfEnabled && !etfLoading;
  const currentReady = listType === 'stock' ? stockReady : etfReady;
  const currentLoading = listType === 'stock' ? loading : etfLoading;
  const currentCached = listType === 'stock' ? cached : etfCached;
  const currentRefresh = listType === 'stock' ? refresh : etfRefresh;

  const handleStockClick = useCallback(
    (code: string, name: string) => {
      navigate(`/?stock=${encodeURIComponent(code)}&name=${encodeURIComponent(name)}`);
    },
    [navigate]
  );

  const groupedStocks = useMemo(() => {
    if (stocks.length === 0 || industries.length === 0) return [];
    return groupStocksByIndustry(stocks, industries, favorites);
  }, [stocks, industries, favorites]);

  const etfCategories = useMemo((): ETFCategoryItem[] => {
    if (etfs.length === 0) return [];
    const typeMap = new Map<string, number>();
    etfs.forEach(etf => {
      typeMap.set(etf.type, (typeMap.get(etf.type) || 0) + 1);
    });
    return Array.from(typeMap.entries())
      .map(([type, count]) => ({ type, count }))
      .sort((a, b) => b.count - a.count);
  }, [etfs]);

  const filteredETFs = useMemo(() => {
    if (!selectedETFType) return etfs;
    return etfs.filter(etf => etf.type === selectedETFType);
  }, [etfs, selectedETFType]);

  return (
    <div className="flex h-[calc(100vh-5rem)] flex-col dark:bg-slate-950 bg-slate-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 sm:px-6 sm:py-4 dark:border-slate-800/80 border-slate-200/60">
        <div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight dark:text-gray-100 text-slate-800">
            {listType === 'stock' ? 'A 股股票' : 'ETF 列表'}
          </h1>
          <p className="text-xs dark:text-slate-500 text-slate-400 mt-1 hidden sm:block">
            {currentReady && currentCached && <span className="text-emerald-500/80">缓存数据</span>}
          </p>
        </div>

        <div className="flex items-center gap-3 sm:gap-4">
          <div className="flex rounded-lg border dark:border-slate-700/80 border-slate-300/70 overflow-hidden">
            <button
              onClick={() => { setListType('stock'); setSelectedETFType(null); localStorage.setItem('stockList_type', 'stock'); }}
              className={`px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-medium transition-all ${listType === 'stock' ? 'bg-cyan-500 text-slate-950 font-semibold' : 'dark:text-slate-400 text-slate-600 dark:hover:bg-slate-800 dark:hover:text-gray-200 hover:bg-slate-200 hover:text-slate-700'}`}
            >
              A 股
            </button>
            <button
              onClick={() => { setListType('etf'); localStorage.setItem('stockList_type', 'etf'); }}
              className={`px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-medium transition-all ${listType === 'etf' ? 'bg-cyan-500 text-slate-950 font-semibold' : 'dark:text-slate-400 text-slate-600 dark:hover:bg-slate-800 dark:hover:text-gray-200 hover:bg-slate-200 hover:text-slate-700'}`}
            >
              ETF
            </button>
          </div>

          <button
            onClick={() => currentRefresh()}
            disabled={currentLoading}
            className="px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg border dark:border-slate-700/80 border-slate-300/70 text-xs sm:text-sm dark:text-slate-300 text-slate-600 dark:hover:bg-slate-800 dark:hover:text-gray-200 hover:bg-slate-200 hover:text-slate-700 disabled:opacity-50 transition-all"
          >
            {currentLoading ? '刷新中...' : '刷新'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-6 mt-4 p-3 rounded-lg dark:bg-red-500/10 bg-red-50/80 dark:text-red-400 text-red-600 dark:border-red-500/20 border-red-200/60 text-sm">
          加载失败: {error.message}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {!currentReady && !currentLoading ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            <div className="text-center">
              <div className="text-5xl mb-4 opacity-20">📭</div>
              <p>暂无数据</p>
            </div>
          </div>
        ) : currentLoading ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            <div className="text-center">
              <div className="text-4xl mb-4 animate-pulse">⏳</div>
              <p>加载中...</p>
            </div>
          </div>
        ) : listType === 'stock' && groupedStocks.length > 0 ? (
          <div className="overflow-y-auto h-full">
            {/* Favorites section at top */}
            <FavoritesSection
              items={groupedStocks[0].stocks}
              favorites={favorites}
              onToggleFavorite={toggleFavorite}
              onStockClick={handleStockClick}
              type="stock"
            />
            {/* Non-favorite stocks grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-2 sm:gap-3 p-3 sm:p-6">
              {groupedStocks[0].stocks
                .filter(stock => !favorites.includes(stock.code))
                .map((stock, index) => (
                  <StockCard
                    key={stock.code}
                    stock={stock as AStockItem}
                    starred={false}
                    onToggleFavorite={toggleFavorite}
                    onStockClick={handleStockClick}
                    index={index}
                  />
                ))}
            </div>
          </div>
        ) : listType === 'etf' ? (
          <div className="flex h-full relative">
            {/* Collapsible sidebar toggle button */}
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className={`absolute top-1/2 -translate-y-1/2 z-20 flex items-center justify-center w-5 h-12 rounded-r-lg dark:bg-slate-800/90 bg-white/90 dark:border-slate-700/50 border-slate-200/60 dark:hover:bg-slate-700/90 hover:bg-slate-100/90 shadow-md transition-all duration-200 ${sidebarCollapsed ? 'left-0' : 'left-32 sm:left-36 md:left-40 lg:left-48'}`}
              title={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}
            >
              <span className={`text-sm dark:text-slate-300 text-slate-600 transition-transform duration-200 ${sidebarCollapsed ? 'rotate-0' : 'rotate-180'}`}>
                ‹
              </span>
            </button>
            <CategoryNav
              categories={etfCategories}
              selectedType={selectedETFType}
              onSelect={setSelectedETFType}
              collapsed={sidebarCollapsed}
            />
            <div className="flex-1 overflow-y-auto">
              <ETFGrid
                etfs={filteredETFs}
                favorites={favorites}
                onToggleFavorite={toggleFavorite}
                onStockClick={handleStockClick}
              />
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-slate-400">
            <div className="text-center">
              <div className="text-5xl mb-4 opacity-20">📭</div>
              <p>暂无数据</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StockListPage;
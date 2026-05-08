/**
 * StockListTable Component
 *
 * Display A-share stock list or ETF list with search and filter
 */

import { useState, useMemo } from 'react';
import type { AStockItem, IndustryItem, ETFItem } from '../hooks/useAStockList';

export interface StockListTableProps {
  stocks?: AStockItem[];
  etfs?: ETFItem[];
  industries: IndustryItem[];
  loading?: boolean;
  onStockClick: (code: string, name: string) => void;
  onIndustryChange: (industry: string | null) => void;
  selectedIndustry: string | null;
  listType?: 'stock' | 'etf';
  favorites?: string[];
  onToggleFavorite?: (code: string) => void;
  showFavoritesOnly?: boolean;
  onShowFavoritesOnlyChange?: (show: boolean) => void;
}

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

const PAGE_SIZE = 50;

export function StockListTable({ stocks = [], etfs = [], industries, loading, onStockClick, onIndustryChange, selectedIndustry, listType = 'stock', favorites = [], onToggleFavorite, showFavoritesOnly = false, onShowFavoritesOnlyChange }: StockListTableProps) {
  const [query, setQuery] = useState('');
  const [marketFilter, setMarketFilter] = useState<string>('');
  const [page, setPage] = useState(1);

  // Get unique markets
  const markets = useMemo(() => {
    if (listType === 'etf') {
      return ['交易所'];
    }
    const set = new Set(stocks.map((s) => s.market));
    return Array.from(set).sort();
  }, [stocks, listType]);

  // Filter stocks/etfs
  const filtered = useMemo((): AStockItem[] | ETFItem[] => {
    if (listType === 'etf') {
      let result = etfs;
      if (showFavoritesOnly) {
        result = result.filter((e) => favorites.includes(e.code));
      }
      if (query.trim()) {
        const q = query.trim().toUpperCase();
        result = result.filter(
          (e) =>
            e.code.toUpperCase().includes(q) ||
            e.name.toUpperCase().includes(q)
        );
      }
      return result;
    }
    let result = stocks;

    if (marketFilter) {
      result = result.filter((s) => s.market === marketFilter);
    }

    if (showFavoritesOnly) {
      result = result.filter((s) => favorites.includes(s.code));
    }

    if (query.trim()) {
      const q = query.trim().toUpperCase();
      result = result.filter(
        (s) =>
          s.code.toUpperCase().includes(q) ||
          s.name.toUpperCase().includes(q) ||
          s.name.includes(query.trim())
      );
    }

    return result;
  }, [stocks, etfs, query, marketFilter, listType, showFavoritesOnly, favorites]);

  // Paginate
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, page]);

  // Reset page when filter changes
  const handleQueryChange = (value: string) => {
    setQuery(value);
    setPage(1);
  };

  const handleMarketChange = (value: string) => {
    setMarketFilter(value);
    setPage(1);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-secondary-text">加载中...</div>
      </div>
    );
  }

  // Not yet loaded (lazy mode: enabled but data not fetched yet)
  const notLoaded = stocks.length === 0 && etfs.length === 0 && !loading;
  if (notLoaded) {
    return (
      <div className="flex items-center justify-center py-12 text-secondary-text">
        请点击上方"加载列表"按钮获取数据
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search and Filter Bar */}
      <div className="flex gap-3 p-4 border-b border-subtle flex-wrap">
        <input
          type="text"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          placeholder={listType === 'etf' ? "搜索 ETF 代码或名称..." : "搜索股票代码或名称..."}
          className="input-surface input-focus-glow h-10 flex-1 min-w-[200px] rounded-xl px-4 text-sm"
        />
        {listType !== 'etf' && (
          <select
            value={marketFilter}
            onChange={(e) => handleMarketChange(e.target.value)}
            className="h-10 rounded-xl border border-subtle bg-surface px-3 text-sm"
          >
            <option value="">全部市场</option>
            {markets.map((m) => (
              <option key={m} value={m}>
                {MARKET_LABELS[m] || m} ({stocks.filter((s) => s.market === m).length})
              </option>
            ))}
          </select>
        )}
        <select
          value={selectedIndustry || ''}
          onChange={(e) => {
            onIndustryChange(e.target.value || null);
            setPage(1);
          }}
          className="h-10 rounded-xl border border-subtle bg-surface px-3 text-sm"
        >
          <option value="">{listType === 'etf' ? '全部类型' : '全部行业'}</option>
          {industries.slice(0, 50).map((ind) => (
            <option key={ind.code} value={ind.name}>
              {ind.name} ({ind.stock_count})
            </option>
          ))}
        </select>
        {favorites.length > 0 && (
          <button
            onClick={() => { onShowFavoritesOnlyChange?.(!showFavoritesOnly); setPage(1); }}
            className={`h-10 rounded-xl border px-3 text-sm flex items-center gap-1.5 ${showFavoritesOnly ? 'border-primary bg-primary/10 text-primary' : 'border-subtle hover:bg-hover'}`}
          >
            <span>★</span>
            <span>{showFavoritesOnly ? '只看收藏' : '收藏'}</span>
            <span className="text-xs opacity-60">({favorites.length})</span>
          </button>
        )}
      </div>

      {/* Results count */}
      <div className="px-4 py-2 text-xs text-secondary-text">
        共 {filtered.length} {listType === 'etf' ? '只 ETF' : '只股票'}
        {selectedIndustry && <span className="ml-2 text-primary">（{selectedIndustry}）</span>}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-surface/95 backdrop-blur">
            <tr className="border-b border-subtle text-left text-secondary-text">
              <th className="px-4 py-2 font-medium w-12"></th>
              <th className="px-4 py-2 font-medium w-28">代码</th>
              <th className="px-4 py-2 font-medium">名称</th>
              <th className="px-4 py-2 font-medium w-24">{listType === 'etf' ? '类型' : '市场'}</th>
            </tr>
          </thead>
          <tbody>
            {listType === 'etf' ? (
              paginated.map((item) => {
                const etf = item as ETFItem;
                const starred = favorites.includes(etf.code);
                return (
                <tr
                  key={etf.code}
                  onClick={() => onStockClick(etf.code, etf.name)}
                  className="border-b border-subtle/50 cursor-pointer hover:bg-primary/5 transition-colors"
                >
                  <td className="px-4 py-2.5">
                    <button
                      onClick={(e) => { e.stopPropagation(); onToggleFavorite?.(etf.code); }}
                      className="text-lg hover:scale-110 transition-transform"
                      title={starred ? '取消收藏' : '添加收藏'}
                    >
                      {starred ? '★' : '☆'}
                    </button>
                  </td>
                  <td className="px-4 py-2.5 font-mono">{etf.code}</td>
                  <td className="px-4 py-2.5">{etf.name}</td>
                  <td className="px-4 py-2.5">
                    <span className="inline-block rounded px-1.5 py-0.5 text-xs bg-green-100 text-green-700">
                      {etf.type}
                    </span>
                  </td>
                </tr>
                );
              })
            ) : (
              paginated.map((item) => {
                const stock = item as AStockItem;
                const starred = favorites.includes(stock.code);
                return (
                <tr
                  key={stock.code}
                  onClick={() => onStockClick(stock.code, stock.name)}
                  className="border-b border-subtle/50 cursor-pointer hover:bg-primary/5 transition-colors"
                >
                  <td className="px-4 py-2.5">
                    <button
                      onClick={(e) => { e.stopPropagation(); onToggleFavorite?.(stock.code); }}
                      className="text-lg hover:scale-110 transition-transform"
                      title={starred ? '取消收藏' : '添加收藏'}
                    >
                      {starred ? '★' : '☆'}
                    </button>
                  </td>
                  <td className="px-4 py-2.5 font-mono">{stock.code}</td>
                  <td className="px-4 py-2.5">{stock.name}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-block rounded px-1.5 py-0.5 text-xs ${
                        stock.market.includes('科创')
                          ? 'bg-purple-100 text-purple-700'
                          : stock.market.includes('创业')
                          ? 'bg-blue-100 text-blue-700'
                          : stock.market.includes('北交')
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {MARKET_LABELS[stock.market] || stock.market}
                    </span>
                  </td>
                </tr>
                );
              })
            )}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div className="flex items-center justify-center py-12 text-secondary-text">
            未找到匹配的{listType === 'etf' ? 'ETF' : '股票'}
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 p-4 border-t border-subtle">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded border border-subtle disabled:opacity-50 hover:bg-hover"
          >
            上一页
          </button>
          <span className="text-sm text-secondary-text">
            第 {page} / {totalPages} 页
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 rounded border border-subtle disabled:opacity-50 hover:bg-hover"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
}

export default StockListTable;

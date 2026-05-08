/**
 * StockListPage
 *
 * A-share stock list and ETF list page with search and filter
 */

import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { StockListTable } from '../components/StockListTable';
import { useAStockList, useIndustryList, useETFList, useETFIndustryList } from '../hooks/useAStockList';
import { useFavorites } from '../hooks';

const StockListPage: React.FC = () => {
  const navigate = useNavigate();
  const [listType, setListType] = useState<'stock' | 'etf'>('stock');
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [stockEnabled, setStockEnabled] = useState(false);
  const [etfEnabled, setEtfEnabled] = useState(false);
  const { stocks, loading, error, cached, refresh } = useAStockList({ industry: selectedIndustry || undefined, enabled: stockEnabled });
  const { industries } = useIndustryList();
  const { etfs, loading: etfLoading, error: etfError, cached: etfCached, refresh: etfRefresh } = useETFList({ etfType: selectedIndustry || undefined, enabled: etfEnabled });
  const { industries: etfIndustries } = useETFIndustryList();
  const { favorites, toggleFavorite } = useFavorites(listType);

  const stockReady = stockEnabled && !loading;
  const etfReady = etfEnabled && !etfLoading;
  const currentReady = listType === 'stock' ? stockReady : etfReady;

  const handleStockClick = useCallback(
    (code: string, name: string) => {
      // Navigate to home with stock code to trigger analysis
      navigate(`/?stock=${encodeURIComponent(code)}&name=${encodeURIComponent(name)}`);
    },
    [navigate]
  );

  const handleIndustryChange = useCallback((industry: string | null) => {
    setSelectedIndustry(industry);
  }, []);

  const currentLoading = listType === 'stock' ? loading : etfLoading;
  const currentError = listType === 'stock' ? error : etfError;
  const currentCached = listType === 'stock' ? cached : etfCached;
  const currentRefresh = listType === 'stock' ? refresh : etfRefresh;
  const currentIndustries = listType === 'stock' ? industries : etfIndustries;

  return (
    <div className="flex h-[calc(100vh-5rem)] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-subtle">
        <div>
          <h1 className="text-lg font-medium">{listType === 'stock' ? 'A 股股票列表' : 'ETF 列表'}</h1>
          <p className="text-xs text-secondary-text">
            点击{listType === 'stock' ? '股票' : 'ETF'}即可分析 {currentCached && <span className="text-success">（缓存数据）</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Tab Switcher */}
          <div className="flex rounded-lg border border-subtle overflow-hidden">
            <button
              onClick={() => { setListType('stock'); setSelectedIndustry(null); setShowFavoritesOnly(false); }}
              className={`px-3 py-1.5 text-sm ${listType === 'stock' ? 'bg-primary text-white' : 'hover:bg-hover'}`}
            >
              A 股
            </button>
            <button
              onClick={() => { setListType('etf'); setSelectedIndustry(null); setShowFavoritesOnly(false); }}
              className={`px-3 py-1.5 text-sm ${listType === 'etf' ? 'bg-primary text-white' : 'hover:bg-hover'}`}
            >
              ETF
            </button>
          </div>
          <button
            onClick={() => currentRefresh()}
            disabled={currentLoading}
            className="px-3 py-1.5 rounded-lg border border-subtle text-sm hover:bg-hover disabled:opacity-50"
          >
            {currentLoading ? '刷新中...' : '刷新列表'}
          </button>
          {!currentReady && (
            <button
              onClick={() => { if (listType === 'stock') { setStockEnabled(true); } else { setEtfEnabled(true); } }}
              className="px-3 py-1.5 rounded-lg bg-primary text-white text-sm hover:bg-primary/90"
            >
              加载列表
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {currentError && (
        <div className="mx-4 mt-4 p-3 rounded-lg bg-danger/10 text-danger text-sm">
          加载失败: {currentError.message}
        </div>
      )}

      {/* Table */}
      <div className="flex-1 overflow-hidden">
        <StockListTable
          stocks={listType === 'stock' ? stocks : []}
          etfs={listType === 'etf' ? etfs : []}
          industries={currentIndustries}
          loading={currentLoading}
          onStockClick={handleStockClick}
          onIndustryChange={handleIndustryChange}
          selectedIndustry={selectedIndustry}
          listType={listType}
          favorites={favorites}
          onToggleFavorite={toggleFavorite}
          showFavoritesOnly={showFavoritesOnly}
          onShowFavoritesOnlyChange={setShowFavoritesOnly}
        />
      </div>
    </div>
  );
};

export default StockListPage;

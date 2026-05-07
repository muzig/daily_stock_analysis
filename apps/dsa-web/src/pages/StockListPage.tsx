/**
 * StockListPage
 *
 * A-share stock list page with search and filter
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { StockListTable } from '../components/StockListTable';
import { useAStockList } from '../hooks/useAStockList';

const StockListPage: React.FC = () => {
  const navigate = useNavigate();
  const { stocks, loading, error, cached, refresh } = useAStockList();

  const handleStockClick = useCallback(
    (code: string, name: string) => {
      // Navigate to home with stock code to trigger analysis
      navigate(`/?stock=${encodeURIComponent(code)}&name=${encodeURIComponent(name)}`);
    },
    [navigate]
  );

  return (
    <div className="flex h-[calc(100vh-5rem)] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-subtle">
        <div>
          <h1 className="text-lg font-medium">A 股股票列表</h1>
          <p className="text-xs text-secondary-text">
            点击股票即可分析 {cached && <span className="text-success">（缓存数据）</span>}
          </p>
        </div>
        <button
          onClick={() => refresh()}
          disabled={loading}
          className="px-3 py-1.5 rounded-lg border border-subtle text-sm hover:bg-hover disabled:opacity-50"
        >
          {loading ? '刷新中...' : '刷新列表'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-4 p-3 rounded-lg bg-danger/10 text-danger text-sm">
          加载失败: {error.message}
        </div>
      )}

      {/* Table */}
      <div className="flex-1 overflow-hidden">
        <StockListTable stocks={stocks} loading={loading} onStockClick={handleStockClick} />
      </div>
    </div>
  );
};

export default StockListPage;

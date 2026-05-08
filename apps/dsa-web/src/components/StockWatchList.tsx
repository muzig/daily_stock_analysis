/**
 * StockWatchList Component
 *
 * Display configured stock watchlist as clickable buttons
 */

console.log('[StockWatchList] Component loaded');

import { useStockWatchList } from '../hooks/useStockWatchList';
import { Loading } from './common';

export interface StockWatchListProps {
  onStockClick: (code: string, name: string) => void;
  disabled?: boolean;
}

export function StockWatchList({ onStockClick, disabled = false }: StockWatchListProps) {
  const { stocks, loading, error } = useStockWatchList();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-3">
        <Loading className="!py-1 !px-3" />
      </div>
    );
  }

  if (error || stocks.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 px-3 py-2">
      {stocks.map((stock) => (
        <button
          key={stock.canonicalCode}
          onClick={() => onStockClick(stock.canonicalCode, stock.name)}
          disabled={disabled}
          className="inline-flex items-center gap-1.5 rounded-lg border border-subtle bg-surface/80 px-3 py-1.5 text-sm text-secondary-text transition-all hover:border-primary hover:bg-primary/5 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span className="font-medium text-foreground">{stock.code}</span>
          <span className="text-xs text-secondary-text/70">{stock.name}</span>
        </button>
      ))}
    </div>
  );
}

export default StockWatchList;

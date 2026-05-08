/**
 * useStockWatchList Hook
 *
 * Fetch and resolve STOCK_LIST from system config
 */

import { useState, useEffect } from 'react';
import { systemConfigApi } from '../api/systemConfig';
import { loadStockIndex } from '../utils/stockIndexLoader';
import type { StockIndexItem } from '../types/stockIndex';

export interface StockWatchItem {
  code: string;
  name: string;
  canonicalCode: string;
}

export interface UseStockWatchListResult {
  stocks: StockWatchItem[];
  loading: boolean;
  error: Error | null;
}

function normalizeCode(code: string): string {
  return code.trim().toUpperCase();
}

function findStockByCode(index: StockIndexItem[], code: string): StockIndexItem | undefined {
  const normalized = normalizeCode(code);
  return index.find(
    (item) =>
      item.displayCode === normalized ||
      item.canonicalCode === normalized ||
      item.canonicalCode.endsWith(`.${normalized}`) ||
      item.pinyinAbbr === normalized ||
      item.pinyinFull === normalized
  );
}

export function useStockWatchList(): UseStockWatchListResult {
  const [stocks, setStocks] = useState<StockWatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        // Fetch system config
        const config = await systemConfigApi.getConfig(false); // includeSchema=false for faster response
        const stockListItem = config.items.find((item) => item.key === 'STOCK_LIST');

        if (!stockListItem || !stockListItem.value) {
          if (mounted) {
            setStocks([]);
            setLoading(false);
          }
          return;
        }

        // Parse stock codes from comma-separated string
        const codes = stockListItem.value
          .split(',')
          .map((c) => c.trim())
          .filter((c) => c);

        if (codes.length === 0) {
          if (mounted) {
            setStocks([]);
            setLoading(false);
          }
          return;
        }

        // Load stock index to resolve names
        const indexResult = await loadStockIndex();
        const index = indexResult.data;

        // Resolve each code to name
        const resolvedStocks: StockWatchItem[] = codes.map((code) => {
          const normalized = normalizeCode(code);
          const indexItem = findStockByCode(index, code);

          return {
            code: normalized,
            name: indexItem?.nameZh || normalized,
            canonicalCode: indexItem?.canonicalCode || normalized,
          };
        });

        if (mounted) {
          setStocks(resolvedStocks);
          setLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      mounted = false;
    };
  }, []);

  return { stocks, loading, error };
}

export default useStockWatchList;

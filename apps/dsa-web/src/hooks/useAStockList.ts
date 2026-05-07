/**
 * useAStockList Hook
 *
 * Fetch A-share stock list from backend API
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api';

export interface AStockItem {
  code: string;
  name: string;
  market: string;
  listing_date?: string;
}

export interface AStockListResponse {
  stocks: AStockItem[];
  total: number;
  cached: boolean;
  cache_time?: string;
}

export interface UseAStockListOptions {
  market?: string;
  forceRefresh?: boolean;
}

export interface UseAStockListResult {
  stocks: AStockItem[];
  loading: boolean;
  error: Error | null;
  total: number;
  cached: boolean;
  refresh: () => void;
}

export function useAStockList(options: UseAStockListOptions = {}): UseAStockListResult {
  const { market, forceRefresh = false } = options;
  const [stocks, setStocks] = useState<AStockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [total, setTotal] = useState(0);
  const [cached, setCached] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const params: Record<string, string | boolean> = {};
        if (market) params.market = market;
        if (forceRefresh) params.force_refresh = true;

        const response = await apiClient.get<AStockListResponse>('/api/v1/stocks/a-list', {
          params,
        });

        if (mounted) {
          setStocks(response.data.stocks || []);
          setTotal(response.data.total || 0);
          setCached(response.data.cached || false);
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
  }, [market, forceRefresh, refreshKey]);

  return { stocks, loading, error, total, cached, refresh };
}

export default useAStockList;

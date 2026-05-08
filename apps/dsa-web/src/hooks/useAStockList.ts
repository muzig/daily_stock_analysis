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

export interface IndustryItem {
  name: string;
  code: string;
  stock_count: number;
}

export interface IndustryListResponse {
  industries: IndustryItem[];
  total: number;
}

export interface ETFItem {
  code: string;
  name: string;
  market: string;
  type: string;
}

export interface ETFListResponse {
  etfs: ETFItem[];
  total: number;
  cached: boolean;
  cache_time?: string;
}

export interface UseAStockListOptions {
  market?: string;
  industry?: string;
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

export interface UseETFListOptions {
  etfType?: string;
  forceRefresh?: boolean;
}

export interface UseETFListResult {
  etfs: ETFItem[];
  loading: boolean;
  error: Error | null;
  total: number;
  cached: boolean;
  refresh: () => void;
}

export function useAStockList(options: UseAStockListOptions = {}): UseAStockListResult {
  const { market, industry, forceRefresh = false } = options;
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
        let response;

        if (industry) {
          // 按行业筛选
          response = await apiClient.get<AStockListResponse>(`/api/v1/stocks/industry/${encodeURIComponent(industry)}`);
        } else {
          // 获取全部或按市场筛选
          const params: Record<string, string | boolean> = {};
          if (market) params.market = market;
          if (forceRefresh) params.force_refresh = true;

          response = await apiClient.get<AStockListResponse>('/api/v1/stocks/a-list', {
            params,
          });
        }

        if (mounted && response) {
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
  }, [market, industry, forceRefresh, refreshKey]);

  return { stocks, loading, error, total, cached, refresh };
}

export function useIndustryList() {
  const [industries, setIndustries] = useState<IndustryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const response = await apiClient.get<IndustryListResponse>('/api/v1/stocks/industries');
        if (mounted) {
          setIndustries(response.data.industries || []);
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

  return { industries, loading, error };
}

export function useETFList(options: UseETFListOptions = {}): UseETFListResult {
  const { etfType, forceRefresh = false } = options;
  const [etfs, setETFs] = useState<ETFItem[]>([]);
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
        if (etfType) params.etf_type = etfType;
        if (forceRefresh) params.force_refresh = true;

        const response = await apiClient.get<ETFListResponse>('/api/v1/stocks/etf-list', {
          params,
        });

        if (mounted && response) {
          setETFs(response.data.etfs || []);
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
  }, [etfType, forceRefresh, refreshKey]);

  return { etfs, loading, error, total, cached, refresh };
}

export function useETFIndustryList() {
  const [industries, setIndustries] = useState<IndustryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const response = await apiClient.get<IndustryListResponse>('/api/v1/stocks/etf-industries');
        if (mounted) {
          setIndustries(response.data.industries || []);
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

  return { industries, loading, error };
}

export default useAStockList;

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
  enabled?: boolean;
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
  enabled?: boolean;
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
  const { market, industry, forceRefresh = false, enabled = true } = options;
  const [stocks, setStocks] = useState<AStockItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [total, setTotal] = useState(0);
  const [cached, setCached] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // 尝试从 localStorage 加载缓存
  const loadCache = useCallback((): AStockItem[] => {
    try {
      const cached = localStorage.getItem('stock_list_cache');
      if (cached) {
        const data = JSON.parse(cached);
        if (Array.isArray(data.stocks)) {
          return data.stocks;
        }
      }
    } catch {}
    return [];
  }, []);

  // 保存到 localStorage
  const saveCache = useCallback((stockList: AStockItem[]) => {
    try {
      localStorage.setItem('stock_list_cache', JSON.stringify({ stocks: stockList }));
    } catch {}
  }, []);

  const refresh = useCallback(() => {
    setIsRefreshing(true);
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (!enabled) return;

    let mounted = true;

    async function load() {
      const cachedStocks = loadCache();

      // 如果有缓存，先立即显示，不显示 loading
      if (cachedStocks.length > 0) {
        setStocks(cachedStocks);
        setTotal(cachedStocks.length);
        setCached(true);
      } else {
        setLoading(true); // 无缓存时显示加载
      }

      setError(null);

      try {
        let response;

        if (industry) {
          response = await apiClient.get<AStockListResponse>(`/api/v1/stocks/industry/${encodeURIComponent(industry)}`);
        } else {
          const params: Record<string, string | boolean> = {};
          if (market) params.market = market;
          if (forceRefresh || isRefreshing) params.force_refresh = true;

          response = await apiClient.get<AStockListResponse>('/api/v1/stocks/a-list', {
            params,
          });
        }

        if (mounted && response) {
          const newStocks = response.data.stocks || [];
          setStocks(newStocks);
          setTotal(response.data.total || 0);
          setCached(response.data.cached || false);
          setLoading(false);
          setIsRefreshing(false);
          saveCache(newStocks);
        }
      } catch (err) {
        if (mounted) {
          if (stocks.length === 0 && cachedStocks.length === 0) {
            setError(err instanceof Error ? err : new Error(String(err)));
          }
          setLoading(false);
          setIsRefreshing(false);
        }
      }
    }

    load();

    return () => {
      mounted = false;
    };
  }, [market, industry, forceRefresh, refreshKey, enabled, isRefreshing, loadCache, saveCache, stocks.length]);

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
  const { etfType, forceRefresh = false, enabled = true } = options;
  const [etfs, setETFs] = useState<ETFItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [total, setTotal] = useState(0);
  const [cached, setCached] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const loadCache = useCallback((): ETFItem[] => {
    try {
      const cached = localStorage.getItem('etf_list_cache');
      if (cached) {
        const data = JSON.parse(cached);
        if (Array.isArray(data.etfs)) {
          return data.etfs;
        }
      }
    } catch {}
    return [];
  }, []);

  const saveCache = useCallback((etfList: ETFItem[]) => {
    try {
      localStorage.setItem('etf_list_cache', JSON.stringify({ etfs: etfList }));
    } catch {}
  }, []);

  const refresh = useCallback(() => {
    setIsRefreshing(true);
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (!enabled) return;

    let mounted = true;

    async function load() {
      const cachedETFs = loadCache();

      // 如果有缓存，先立即显示，不显示 loading
      if (cachedETFs.length > 0) {
        setETFs(cachedETFs);
        setTotal(cachedETFs.length);
        setCached(true);
      } else {
        setLoading(true); // 无缓存时显示加载
      }

      // 只有手动刷新时才请求后端
      if (!isRefreshing) {
        setLoading(false);
        setIsRefreshing(false);
        return;
      }

      setError(null);

      try {
        const params: Record<string, string | boolean> = {};
        if (etfType) params.etf_type = etfType;
        if (isRefreshing) params.force_refresh = true;

        const response = await apiClient.get<ETFListResponse>('/api/v1/stocks/etf-list', {
          params,
        });

        if (mounted && response) {
          const newETFs = response.data.etfs || [];
          setETFs(newETFs);
          setTotal(response.data.total || 0);
          setCached(response.data.cached || false);
          setLoading(false);
          setIsRefreshing(false);
          saveCache(newETFs);
        }
      } catch (err) {
        if (mounted) {
          if (etfs.length === 0 && cachedETFs.length === 0) {
            setError(err instanceof Error ? err : new Error(String(err)));
          }
          setLoading(false);
          setIsRefreshing(false);
        }
      }
    }

    load();

    return () => {
      mounted = false;
    };
  }, [etfType, forceRefresh, refreshKey, enabled, isRefreshing, loadCache, saveCache, etfs.length]);

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

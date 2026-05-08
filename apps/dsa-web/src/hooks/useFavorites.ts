import { useState, useCallback, useEffect } from 'react';

const STORAGE_KEY_STOCKS = 'dsa_favorites_stocks';
const STORAGE_KEY_ETFS = 'dsa_favorites_etfs';

function loadFavorites(key: string): string[] {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveFavorites(key: string, values: string[]) {
  localStorage.setItem(key, JSON.stringify(values));
}

export function useFavorites(type: 'stock' | 'etf') {
  const storageKey = type === 'stock' ? STORAGE_KEY_STOCKS : STORAGE_KEY_ETFS;
  const [favorites, setFavorites] = useState<string[]>(() => loadFavorites(storageKey));

  useEffect(() => {
    saveFavorites(storageKey, favorites);
  }, [storageKey, favorites]);

  const toggleFavorite = useCallback((code: string) => {
    setFavorites((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  }, []);

  const isFavorite = useCallback((code: string) => favorites.includes(code), [favorites]);

  return { favorites, toggleFavorite, isFavorite };
}

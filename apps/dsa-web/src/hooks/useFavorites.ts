import { useState, useCallback, useEffect } from 'react';
import { getFavorites, addFavorite, removeFavorite } from '../api/favorites';

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
  const [synced, setSynced] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  // Load from backend on mount, keep localStorage as fallback
  useEffect(() => {
    let cancelled = false;
    setSynced(false);
    setSyncError(null);

    getFavorites()
      .then((data) => {
        if (cancelled) return;
        const list = type === 'stock' ? data.stocks : data.etfs;
        setFavorites(list);
        saveFavorites(storageKey, list);
        setSynced(true);
      })
      .catch((err) => {
        if (cancelled) return;
        console.warn('[useFavorites] sync failed, using localStorage:', err);
        setSynced(true);
        setSyncError(err instanceof Error ? err.message : String(err));
      });

    return () => {
      cancelled = true;
    };
  }, [storageKey, type]);

  // Keep localStorage in sync with current state
  useEffect(() => {
    if (synced) {
      saveFavorites(storageKey, favorites);
    }
  }, [storageKey, favorites, synced]);

  const toggleFavorite = useCallback(
    async (code: string) => {
      const isFav = favorites.includes(code);

      // Optimistic local update
      setFavorites((prev) =>
        prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
      );

      // Sync to backend
      try {
        if (isFav) {
          await removeFavorite(code, type);
        } else {
          await addFavorite(code, type);
        }
      } catch {
        // Backend failed — local state already updated, will retry on next load
      }
    },
    [favorites, type]
  );

  const isFavorite = useCallback((code: string) => favorites.includes(code), [favorites]);

  return { favorites, toggleFavorite, isFavorite, syncError };
}
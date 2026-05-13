import apiClient from './index';

const DEVICE_ID_KEY = 'dsa_device_id';

function getDeviceId(): string {
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

function favoritesHeaders() {
  return { 'X-Device-ID': getDeviceId() };
}

export interface FavoritesResponse {
  stocks: string[];
  etfs: string[];
}

export interface AddFavoriteRequest {
  code: string;
  type: 'stock' | 'etf';
}

export async function getFavorites(): Promise<FavoritesResponse> {
  const { data } = await apiClient.get<FavoritesResponse>('/api/v1/favorites', {
    headers: favoritesHeaders(),
  });
  return data;
}

export async function addFavorite(code: string, type: 'stock' | 'etf'): Promise<void> {
  await apiClient.post<void>(
    '/api/v1/favorites',
    { code, type } as AddFavoriteRequest,
    { headers: favoritesHeaders() }
  );
}

export async function removeFavorite(code: string, type: 'stock' | 'etf' = 'stock'): Promise<void> {
  await apiClient.delete(`/api/v1/favorites/${code}?type=${type}`, {
    headers: favoritesHeaders(),
  });
}
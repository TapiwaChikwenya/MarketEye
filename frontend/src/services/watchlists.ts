import { api } from '@/lib/axios';
import { Watchlist, WatchlistWithAssets, Asset } from '@/types';

export interface CreateWatchlistData {
  name: string;
  description?: string;
}

export interface UpdateWatchlistData {
  name?: string;
  description?: string;
  sort_order?: number;
}

export interface AddAssetBySymbolData {
  symbol: string;
  name?: string;
  asset_type?: string;
  exchange?: string;
  sort_order?: number;
}

export interface WatchlistWithAssetsDetail {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  sort_order?: number;
  assets: Asset[];
}

export const watchlistsService = {
  async getWatchlists(): Promise<Watchlist[]> {
    const response = await api.get<Watchlist[]>('/watchlists/');
    return response.data;
  },

  async getWatchlist(watchlistId: string): Promise<WatchlistWithAssetsDetail> {
    const response = await api.get<WatchlistWithAssetsDetail>(`/watchlists/${watchlistId}`);
    return response.data;
  },

  async createWatchlist(data: CreateWatchlistData): Promise<Watchlist> {
    const response = await api.post<Watchlist>('/watchlists/', data);
    return response.data;
  },

  async updateWatchlist(watchlistId: string, data: UpdateWatchlistData): Promise<Watchlist> {
    const response = await api.put<Watchlist>(`/watchlists/${watchlistId}`, data);
    return response.data;
  },

  async deleteWatchlist(watchlistId: string): Promise<void> {
    await api.delete(`/watchlists/${watchlistId}`);
  },

  async addAssetToWatchlist(watchlistId: string, assetId: string, sortOrder: number = 0): Promise<void> {
    await api.post(`/watchlists/${watchlistId}/assets`, {
      asset_id: assetId,
      sort_order: sortOrder,
    });
  },

  async addAssetBySymbol(watchlistId: string, data: AddAssetBySymbolData): Promise<{ message: string; asset_id: string }> {
    const response = await api.post<{ message: string; asset_id: string }>(
      `/watchlists/${watchlistId}/assets/by-symbol`,
      data
    );
    return response.data;
  },

  async removeAssetFromWatchlist(watchlistId: string, assetId: string): Promise<void> {
    await api.delete(`/watchlists/${watchlistId}/assets/${assetId}`);
  },

  async removeAssetBySymbol(watchlistId: string, symbol: string): Promise<void> {
    await api.delete(`/watchlists/${watchlistId}/assets/by-symbol/${symbol}`);
  },
};


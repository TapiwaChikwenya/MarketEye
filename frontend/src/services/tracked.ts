import { api } from '@/lib/axios';

export interface TrackedAsset {
  id: string;
  symbol: string;
  name: string;
  asset_type: 'STOCK' | 'CRYPTO' | 'ETF' | 'MUTUAL_FUND' | 'INDEX';
  exchange?: string;
  tracked_at: string;
  // Live data (added client-side)
  current_price?: string;
  change_percent_24h?: string;
}

export interface TrackAssetData {
  symbol: string;
  name: string;
  asset_type: string;
  exchange?: string;
}

export const trackedService = {
  async getTrackedAssets(): Promise<TrackedAsset[]> {
    const response = await api.get<TrackedAsset[]>('/tracked/');
    return response.data;
  },

  async trackAsset(data: TrackAssetData): Promise<TrackedAsset> {
    const response = await api.post<TrackedAsset>('/tracked/', data);
    return response.data;
  },

  async untrackAsset(symbol: string): Promise<void> {
    await api.delete(`/tracked/${symbol}`);
  },

  async syncTrackedAssets(assets: TrackAssetData[]): Promise<TrackedAsset[]> {
    const response = await api.post<TrackedAsset[]>('/tracked/sync', assets);
    return response.data;
  },
};


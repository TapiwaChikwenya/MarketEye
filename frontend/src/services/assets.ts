import { api } from '@/lib/axios';
import { Asset, HistoricalDataPoint } from '@/types';

export const assetsService = {
  async searchAssets(query: string, assetType?: string): Promise<Asset[]> {
    const params: Record<string, string> = { q: query };
    if (assetType) params.asset_type = assetType;

    const response = await api.get<Asset[]>('/assets/search', { params });
    return response.data;
  },

  async getAsset(assetId: string): Promise<Asset> {
    const response = await api.get<Asset>(`/assets/${assetId}`);
    return response.data;
  },

  async getAssetPrice(assetId: string): Promise<Record<string, unknown>> {
    const response = await api.get(`/assets/${assetId}/price`);
    return response.data;
  },

  async getAssetHistory(
    assetId: string,
    period: string = '1mo',
    interval: string = '1d'
  ): Promise<{ data: HistoricalDataPoint[] }> {
    const response = await api.get(`/assets/${assetId}/history`, {
      params: { period, interval },
    });
    return response.data;
  },
};

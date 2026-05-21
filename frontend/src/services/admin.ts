import { api } from '@/lib/axios';

export interface AdminOverview {
  users_total: number;
  users_active: number;
  users_new_24h: number;
  users_new_7d: number;
  alerts_total: number;
  alerts_active: number;
  tracked_assets_rows: number;
  tracked_unique_symbols: number;
  watchlists_total: number;
  notification_logs_24h: number;
  trending_cache_hits: number;
  trending_cache_misses: number;
}

export interface AdminUserRow {
  id: string;
  email: string;
  name?: string;
  is_active: boolean;
  is_superuser: boolean;
  subscription_tier: string;
  created_at?: string | null;
}

export interface AdminUserList {
  items: AdminUserRow[];
  total: number;
  skip: number;
  limit: number;
}

export interface AdminSystemHealth {
  uptime_seconds: number;
  api_version: string;
  database_latency_ms: number | null;
  database_ok: boolean;
  redis_latency_ms: number | null;
  redis_ok: boolean;
  redis_error: string | null;
  ttl_seconds: Record<string, number>;
}

export interface AdminStocksUsage {
  unique_symbols_tracked: number;
  top_symbols: { symbol: string; track_count: number }[];
}

export const adminService = {
  async getOverview(): Promise<AdminOverview> {
    const { data } = await api.get<AdminOverview>('/admin/overview');
    return data;
  },

  async getUsers(skip = 0, limit = 50): Promise<AdminUserList> {
    const { data } = await api.get<AdminUserList>('/admin/users', { params: { skip, limit } });
    return data;
  },

  async patchUser(
    userId: string,
    patch: { is_active?: boolean; is_superuser?: boolean }
  ): Promise<AdminUserRow> {
    const { data } = await api.patch<AdminUserRow>(`/admin/users/${userId}`, patch);
    return data;
  },

  async getSystemHealth(): Promise<AdminSystemHealth> {
    const { data } = await api.get<AdminSystemHealth>('/admin/system/health');
    return data;
  },

  async getStocksUsage(): Promise<AdminStocksUsage> {
    const { data } = await api.get<AdminStocksUsage>('/admin/stocks/usage');
    return data;
  },
};

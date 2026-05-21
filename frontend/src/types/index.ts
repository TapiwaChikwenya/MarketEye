export interface User {
  id: string;
  email: string;
  name?: string;
  phone_number?: string;
  preferred_contact_method: 'SMS' | 'CALL' | 'PUSH' | 'EMAIL';
  time_zone: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  subscription_tier: 'free' | 'pro';
  is_active: boolean;
  is_superuser?: boolean;
  email_verified: boolean;
  phone_verified: boolean;
}

export interface Asset {
  id: string;
  symbol: string;
  name: string;
  asset_type: 'STOCK' | 'CRYPTO' | 'ETF' | 'MUTUAL_FUND' | 'INDEX';
  exchange?: string;
  currency: string;
  current_price?: string;
  market_cap?: string;
  volume_24h?: string;
  change_24h?: string;
  change_percent_24h?: string;
  last_updated?: string;
  created_at: string;
}

export interface Watchlist {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  sort_order?: number;
  created_at: string;
  updated_at?: string;
}

export interface WatchlistWithAssets extends Watchlist {
  asset_ids: string[];
}

export interface AlertRule {
  id: string;
  user_id: string;
  asset_id?: string;
  name?: string;
  condition_type: string;
  threshold_value: string;
  lookback_period?: string;
  notification_channel: 'SMS' | 'CALL' | 'PUSH' | 'EMAIL' | 'MULTI';
  repeat_behavior: 'one_time' | 'once_per_day' | 'once_per_hour' | 'unlimited';
  is_active: boolean;
  last_triggered_at?: string;
  trigger_count: number;
  override_quiet_hours: boolean;
  custom_message?: string;
  created_at: string;
  updated_at?: string;
}

export interface Portfolio {
  id: string;
  user_id: string;
  name: string;
  total_cost_basis: string;
  current_value: string;
  unrealized_pnl: string;
  unrealized_pnl_percent: string;
  created_at: string;
  updated_at?: string;
  last_calculated_at?: string;
}

export interface PortfolioHolding {
  id: string;
  portfolio_id: string;
  asset_id: string;
  quantity: string;
  average_cost_basis: string;
  total_cost_basis: string;
  purchase_date?: string;
  current_price?: string;
  current_value?: string;
  unrealized_pnl?: string;
  unrealized_pnl_percent?: string;
  created_at: string;
  updated_at?: string;
}

export interface HistoricalDataPoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

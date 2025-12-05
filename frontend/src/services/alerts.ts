import { api } from '@/lib/axios';
import { AlertRule } from '@/types';

export type ConditionType = 
  | 'PRICE_ABOVE'
  | 'PRICE_BELOW'
  | 'PERCENT_CHANGE_UP'
  | 'PERCENT_CHANGE_DOWN'
  | 'VOLUME_ABOVE'
  | 'MARKET_CAP_ABOVE'
  | 'PORTFOLIO_VALUE_UP'
  | 'PORTFOLIO_VALUE_DOWN';

export type NotificationChannel = 'SMS' | 'CALL' | 'PUSH' | 'EMAIL' | 'MULTI';
export type RepeatBehavior = 'ONE_TIME' | 'ONCE_PER_DAY' | 'ONCE_PER_HOUR' | 'UNLIMITED';

export interface CreateAlertData {
  asset_id?: string;
  name?: string;
  condition_type: ConditionType;
  threshold_value: string;
  lookback_period?: string;
  notification_channel?: NotificationChannel;
  repeat_behavior?: RepeatBehavior;
  override_quiet_hours?: boolean;
  custom_message?: string;
}

export interface UpdateAlertData {
  name?: string;
  threshold_value?: string;
  notification_channel?: NotificationChannel;
  repeat_behavior?: RepeatBehavior;
  is_active?: boolean;
  override_quiet_hours?: boolean;
  custom_message?: string;
}

export const alertsService = {
  async getAlerts(): Promise<AlertRule[]> {
    const response = await api.get<AlertRule[]>('/alerts/');
    return response.data;
  },

  async getAlert(alertId: string): Promise<AlertRule> {
    const response = await api.get<AlertRule>(`/alerts/${alertId}`);
    return response.data;
  },

  async createAlert(data: CreateAlertData): Promise<AlertRule> {
    // Backend expects: condition_type=lowercase, notification_channel=UPPERCASE, repeat_behavior=lowercase
    const payload = {
      ...data,
      condition_type: data.condition_type.toLowerCase().replace(/_/g, '_'),
      notification_channel: data.notification_channel?.toUpperCase(),
      repeat_behavior: data.repeat_behavior?.toLowerCase().replace(/_/g, '_'),
    };
    const response = await api.post<AlertRule>('/alerts/', payload);
    return response.data;
  },

  async updateAlert(alertId: string, data: UpdateAlertData): Promise<AlertRule> {
    // Backend expects: notification_channel=UPPERCASE, repeat_behavior=lowercase
    const payload: Record<string, unknown> = { ...data };
    if (data.notification_channel) {
      payload.notification_channel = data.notification_channel.toUpperCase();
    }
    if (data.repeat_behavior) {
      payload.repeat_behavior = data.repeat_behavior.toLowerCase().replace(/_/g, '_');
    }
    const response = await api.put<AlertRule>(`/alerts/${alertId}`, payload);
    return response.data;
  },

  async deleteAlert(alertId: string): Promise<void> {
    await api.delete(`/alerts/${alertId}`);
  },

  async toggleAlert(alertId: string, isActive: boolean): Promise<AlertRule> {
    return this.updateAlert(alertId, { is_active: isActive });
  },
};

export const CONDITION_TYPE_LABELS: Record<ConditionType, string> = {
  PRICE_ABOVE: 'Price goes above',
  PRICE_BELOW: 'Price goes below',
  PERCENT_CHANGE_UP: 'Price increases by %',
  PERCENT_CHANGE_DOWN: 'Price decreases by %',
  VOLUME_ABOVE: 'Volume exceeds',
  MARKET_CAP_ABOVE: 'Market cap exceeds',
  PORTFOLIO_VALUE_UP: 'Portfolio value increases by %',
  PORTFOLIO_VALUE_DOWN: 'Portfolio value decreases by %',
};


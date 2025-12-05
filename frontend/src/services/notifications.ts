import { api } from '@/lib/axios';

export interface Notification {
  id: string;
  event_type: string;
  status: string;
  subject?: string;
  message: string;
  symbol?: string;
  asset_name?: string;
  created_at: string;
  sent_at?: string;
}

export interface NotificationSummary {
  total: number;
  sent: number;
  failed: number;
  recent: Notification[];
}

export interface TestNotificationData {
  channel: 'PUSH' | 'EMAIL' | 'SMS';
  message?: string;
}

export interface TestNotificationResponse {
  status: string;
  channel: string;
  data?: {
    title: string;
    body: string;
    timestamp: string;
  };
  result?: Record<string, unknown>;
}

export const notificationsService = {
  async getNotifications(limit: number = 50): Promise<Notification[]> {
    const response = await api.get<Notification[]>('/notifications/', {
      params: { limit },
    });
    return response.data;
  },

  async getNotificationSummary(): Promise<NotificationSummary> {
    const response = await api.get<NotificationSummary>('/notifications/summary');
    return response.data;
  },

  async sendTestNotification(data: TestNotificationData): Promise<TestNotificationResponse> {
    const response = await api.post<TestNotificationResponse>('/notifications/test', data);
    return response.data;
  },
};


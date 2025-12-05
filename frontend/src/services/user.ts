import { api } from '@/lib/axios';
import { User } from '@/types';

export interface UpdateUserData {
  name?: string;
  phone_number?: string;
  preferred_contact_method?: 'SMS' | 'CALL' | 'PUSH' | 'EMAIL';
  time_zone?: string;
  quiet_hours_enabled?: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
}

export const userService = {
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/users/me');
    return response.data;
  },

  async updateUser(data: UpdateUserData): Promise<User> {
    const response = await api.put<User>('/users/me', data);
    return response.data;
  },
};

export const CONTACT_METHODS = [
  { value: 'EMAIL', label: 'Email' },
  { value: 'SMS', label: 'SMS' },
  { value: 'CALL', label: 'Phone Call' },
  { value: 'PUSH', label: 'Push Notification' },
];

export const TIME_ZONES = [
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'Europe/London', label: 'London (GMT/BST)' },
  { value: 'Europe/Paris', label: 'Central European Time (CET)' },
  { value: 'Asia/Tokyo', label: 'Japan Standard Time (JST)' },
  { value: 'Asia/Shanghai', label: 'China Standard Time (CST)' },
  { value: 'Australia/Sydney', label: 'Australian Eastern Time (AET)' },
];


import axios from 'axios';
import { API_URL } from '@/lib/api-config';

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const reqUrl = String(error.config?.url ?? '');
      // Failed login/register returns 401 — do not wipe session or hard-redirect
      if (reqUrl.includes('/auth/login') || reqUrl.includes('/auth/register')) {
        return Promise.reject(error);
      }
      localStorage.removeItem('token');
      const path = window.location.pathname + window.location.search;
      if (window.location.pathname === '/login' || window.location.pathname === '/register') {
        window.location.href = window.location.pathname;
      } else {
        window.location.href = `/login?returnTo=${encodeURIComponent(path)}`;
      }
    }
    // 403: stay on page (e.g. non-admin hitting admin API)
    return Promise.reject(error);
  }
);

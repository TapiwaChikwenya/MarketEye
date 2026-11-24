/**
 * API origin used by the SPA.
 *
 * Dev (vite): unset VITE_API_URL means http://<page-hostname>:8000 so a phone
 * on the LAN can open the UI at http://<pc-ip>:5173 and still reach the API.
 * A configured localhost URL is rewritten to that hostname for the same reason.
 *
 * Prod build: unset VITE_API_URL means same-origin (empty prefix), which matches
 * the nginx proxy that serves /api on the UI host.
 */
function resolveApiUrl(): string {
  const configured = String(import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
  if (typeof window === 'undefined') {
    return configured;
  }

  const pageHost = window.location.hostname;
  const pageIsLoopback = pageHost === 'localhost' || pageHost === '127.0.0.1';

  if (!configured) {
    if (import.meta.env.PROD) {
      return '';
    }
    return `${window.location.protocol}//${pageHost}:8000`;
  }

  try {
    const url = new URL(configured);
    const configIsLoopback = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
    if (configIsLoopback && !pageIsLoopback) {
      url.hostname = pageHost;
      return url.origin;
    }
  } catch {
    return configured;
  }
  return configured;
}

export const API_URL = resolveApiUrl();

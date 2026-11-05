/**
 * API configuration and helper utilities for YatraSathi Web.
 * Supports configurable VITE_API_BASE_URL for decoupled deployments
 * (e.g. Vercel frontend + Render/Railway backend), defaulting to
 * relative paths for same-origin or reverse-proxied production setups.
 */
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

export function apiUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${cleanPath}` : cleanPath;
}

/**
 * Turn a FastAPI error body into a user-facing message.
 * Handles `{"detail": "text"}` and validation errors
 * (`{"detail": [{"msg": "...", "loc": [...]}, ...]}`).
 */
export function apiErrorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((d) => {
        const msg = typeof d?.msg === 'string' ? d.msg.replace(/^Value error, /, '') : '';
        const field = Array.isArray(d?.loc) ? d.loc[d.loc.length - 1] : '';
        return field && typeof field === 'string' && !msg.toLowerCase().includes(field) ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean)
      .join(' ');
  }
  return fallback;
}

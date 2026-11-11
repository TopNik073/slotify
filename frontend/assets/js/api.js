const API_ROOT = '/api/v1';

const ACCESS_KEY = 'slotify.accessToken';
const REFRESH_KEY = 'slotify.refreshToken';
let sessionRevision = 0;
let redirectingToLogin = false;

export const session = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  get isAuthenticated() {
    return Boolean(this.access || this.refresh);
  },
  save(accessToken, refreshToken) {
    sessionRevision++;
    localStorage.setItem(ACCESS_KEY, accessToken);
    localStorage.setItem(REFRESH_KEY, refreshToken);
  },
  clear() {
    sessionRevision++;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export function redirectToLogin({ expired = false } = {}) {
  if (redirectingToLogin) return;
  redirectingToLogin = true;
  session.clear();
  const query = new URLSearchParams();
  if (expired) query.set('session', 'expired');
  if (!['/login.html', '/register.html', '/auth-callback.html', '/'].includes(window.location.pathname)) {
    query.set('next', window.location.pathname + window.location.search);
  }
  window.location.replace(`/login.html${query.size ? `?${query}` : ''}`);
}

export class ApiError extends Error {
  constructor(status, code, detail) {
    super(detail || code || `Request failed with ${status}`);
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

function buildUrl(path, query) {
  const url = new URL(API_ROOT + path, window.location.origin);

  for (const [key, value] of Object.entries(query || {})) {
    if (value === undefined || value === null || value === '') continue;

    if (Array.isArray(value)) {
      value.forEach((item) => url.searchParams.append(key, item));
    } else {
      url.searchParams.set(key, value);
    }
  }

  return url;
}

// Share a refresh across concurrent requests, including those sent after an idle tab wakes up.
let refreshInFlight = null;

function expiresSoon(token) {
  try {
    const encoded = token.split('.')[1].replaceAll('-', '+').replaceAll('_', '/');
    const { exp } = JSON.parse(atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, '=')));
    // This is only a scheduling hint. The server still verifies the JWT and its signature.
    return Number.isFinite(exp) && exp * 1000 <= Date.now() + 30000;
  } catch {
    return false;
  }
}

function isAuthenticationError(response, payload) {
  // Also accept the legacy error code while an older server or page is still running.
  return response.status === 401 || payload.code === 'invalid_token';
}

function expiredSession() {
  redirectToLogin({ expired: true });
  return new ApiError(401, 'session_expired', 'Сессия истекла. Войдите снова.');
}

async function refreshTokens() {
  const refreshToken = session.refresh;
  if (!refreshToken) throw expiredSession();

  if (!refreshInFlight) {
    const revision = sessionRevision;
    refreshInFlight = (async () => {
      const response = await fetch(`${API_ROOT}/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken }),
      });
      const data = await response.json().catch(() => ({}));
      // A late refresh must never sign the user back in after logout or replace a newer login.
      if (sessionRevision !== revision || session.refresh !== refreshToken) {
        throw new ApiError(409, 'session_changed', 'Сессия изменилась. Обновите страницу.');
      }
      if (!response.ok) {
        if (isAuthenticationError(response, data)) throw expiredSession();
        throw new ApiError(response.status, data.code, data.detail);
      }
      if (typeof data.accessToken !== 'string' || !data.accessToken ||
          typeof data.refreshToken !== 'string' || !data.refreshToken) {
        throw new ApiError(502, 'invalid_token_response', 'Не удалось обновить сессию. Попробуйте ещё раз.');
      }
      session.save(data.accessToken, data.refreshToken);
    })().finally(() => {
      refreshInFlight = null;
    });
  }

  return refreshInFlight;
}

async function request(path, { method = 'GET', body, query, auth = true, retry = true, keepalive = false } = {}) {
  if (auth && (!session.access || expiresSoon(session.access))) await refreshTokens();
  const accessToken = auth ? session.access : null;
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const response = await fetch(buildUrl(path, query), {
    method,
    headers,
    keepalive,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 204) return null;

  const payload = await response.json().catch(() => ({}));

  if (auth && isAuthenticationError(response, payload)) {
    if (!retry) throw expiredSession();
    // Another request may already have refreshed the access token while this one was in flight.
    if (session.access === accessToken) await refreshTokens();
    if (!session.access) throw expiredSession();
    return request(path, { method, body, query, auth, retry: false, keepalive });
  }

  if (!response.ok) {
    throw new ApiError(response.status, payload.code, payload.detail);
  }

  return payload;
}

export const api = {
  auth: {
    register: (payload) => request('/auth/register/', { method: 'POST', body: payload, auth: false }),
    login: (email, password) =>
      request('/auth/login/', { method: 'POST', body: { email, password }, auth: false }),
    restore: (email, newPassword) =>
      request('/auth/restore/', { method: 'POST', body: { email, newPassword }, auth: false }),
    confirm: (operation, payload) =>
      request(`/auth/2fa/${operation}`, { method: 'POST', body: payload, auth: false }),
    googleLoginUrl: (email, next) => request('/auth/google/login', { query: { email, next }, auth: false }),
    disconnectGoogle: () => request('/auth/google/', { method: 'DELETE' }),
  },

  users: {
    me: () => request('/users/me'),
    updateMe: (payload, { keepalive = false } = {}) => request('/users/me', { method: 'PATCH', body: payload, keepalive }),
    search: (q, officeId) => request('/users/search', { query: { q, officeId } }),
  },

  offices: {
    list: (includeInactive = false) => request('/offices/', { query: { includeInactive }, auth: false }),
    timezones: () => request('/offices/timezones', { auth: false }),
  },

  rooms: {
    list: (query) => request('/rooms/', { query }),
    availability: (officeId, day, minCapacity) =>
      request('/rooms/availability', { query: { officeId, day, minCapacity } }),
    free: (officeId, startsAt, endsAt, minCapacity) =>
      request('/rooms/free', { query: { officeId, startsAt, endsAt, minCapacity } }),
  },

  equipment: {
    list: (query) => request('/equipment/', { query }),
    free: (officeId, startsAt, endsAt, roomId) =>
      request('/equipment/free', { query: { officeId, startsAt, endsAt, roomId } }),
  },

  bookings: {
    create: (payload) => request('/bookings/', { method: 'POST', body: payload }),
    list: (query) => request('/bookings/', { query }),
    get: (id) => request(`/bookings/${id}`),
    reschedule: (id, startsAt, endsAt) =>
      request(`/bookings/${id}`, { method: 'PATCH', body: { startsAt, endsAt } }),
    cancel: (id, wholeSeries = false) =>
      request(`/bookings/${id}`, { method: 'DELETE', query: { wholeSeries } }),
    respond: (id, response) =>
      request(`/bookings/${id}/response`, { method: 'POST', body: { response } }),
  },

  admin: {
    createOffice: (payload) => request('/admin/offices/', { method: 'POST', body: payload }),
    updateOffice: (id, payload) => request(`/admin/offices/${id}`, { method: 'PATCH', body: payload }),
    deleteOffice: (id) => request(`/admin/offices/${id}`, { method: 'DELETE' }),

    createRoom: (payload) => request('/admin/rooms/', { method: 'POST', body: payload }),
    updateRoom: (id, payload) => request(`/admin/rooms/${id}`, { method: 'PATCH', body: payload }),
    deleteRoom: (id) => request(`/admin/rooms/${id}`, { method: 'DELETE' }),

    createEquipment: (payload) => request('/admin/equipment/', { method: 'POST', body: payload }),
    updateEquipment: (id, payload) => request(`/admin/equipment/${id}`, { method: 'PATCH', body: payload }),
    deleteEquipment: (id) => request(`/admin/equipment/${id}`, { method: 'DELETE' }),

    listUsers: (query) => request('/admin/users/', { query }),
    updateUser: (id, payload) => request(`/admin/users/${id}`, { method: 'PATCH', body: payload }),
    deleteUser: (id) => request(`/admin/users/${id}`, { method: 'DELETE' }),
  },
};

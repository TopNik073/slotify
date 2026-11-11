import { api, ApiError, redirectToLogin } from './api.js';

/** Send unauthenticated visitors to the login page, and hand the current user to the page. */
export async function requireAuth({ adminOnly = false } = {}) {
  renderNav();

  try {
    const me = await api.users.me();

    if (adminOnly && me.role !== 'admin') {
      window.location.replace('/rooms.html');
      return null;
    }

    renderNav(me);
    return me;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      redirectToLogin({ expired: true });
      return null;
    }

    throw error;
  }
}

export function renderNav(me = null) {
  const nav = document.querySelector('[data-nav]');
  if (!nav) return;

  const links = [
    ['/rooms.html', 'Бронирование', 'calendar'],
    ['/my-bookings.html', 'Мои встречи', 'bookings'],
  ];
  if (me?.role === 'admin') links.push(['/admin.html', 'Управление', 'settings']);

  const current = window.location.pathname;
  nav.innerHTML = `
    <a class="brand" href="/index.html">${brandMark()}slotify</a>
    <span class="nav-caption">РАБОЧЕЕ ПРОСТРАНСТВО</span>
    <div class="nav-links" role="group" aria-label="Разделы приложения" tabindex="0">
      ${links
        .map(
          ([href, label, symbol]) =>
            `<a href="${href}" ${current === href ? 'aria-current="page"' : ''} class="${current === href ? 'active' : ''}">${icon(symbol)}${label}</a>`,
        )
        .join('')}
    </div>
    <div class="nav-note">
      <p>Идеям нужно<br>место.</p>
      <small>А встречам — подходящее время.</small>
    </div>
    <div class="nav-user">
      ${me ? `<span class="avatar" data-avatar aria-hidden="true"></span>
      <div class="user-copy"><strong>${escapeHtml(me.fullName || me.email)}</strong><small>${me.role === 'admin' ? 'Администратор' : 'Личное пространство'}</small></div>` : '<div class="user-copy"><strong>Проверяем сессию…</strong></div>'}
    </div>
    <button type="button" data-logout class="logout">${icon('logout')}<span>Выйти из аккаунта</span></button>
  `;

  if (me) renderAvatar(nav.querySelector('[data-avatar]'), me);

  const strip = nav.querySelector('.nav-links');
  const active = strip.querySelector('[aria-current="page"]');
  if (active && strip.scrollWidth > strip.clientWidth) {
    const stripBounds = strip.getBoundingClientRect();
    const activeBounds = active.getBoundingClientRect();
    if (activeBounds.right > stripBounds.right) strip.scrollLeft += activeBounds.right - stripBounds.right;
    else if (activeBounds.left < stripBounds.left) strip.scrollLeft -= stripBounds.left - activeBounds.left;
  }

  nav.querySelector('[data-logout]').addEventListener('click', () => {
    redirectToLogin();
  });
}

export function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value ?? '';
  return div.innerHTML.replaceAll('"', '&quot;').replaceAll("'", '&#39;');
}

export function initials(name) {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
}

export function brandMark() {
  return '<img class="brand-mark" src="/assets/favicon.svg" alt="" width="28" height="28" />';
}

export function renderAvatar(element, user) {
  element.textContent = initials(user.fullName || user.email);
  if (!user.avatarUrl) return;
  let url;
  try { url = new URL(user.avatarUrl, window.location.origin); } catch { return; }
  if (!['http:', 'https:'].includes(url.protocol)) return;
  const photo = document.createElement('img');
  photo.src = url.href;
  photo.alt = '';
  photo.referrerPolicy = 'no-referrer';
  photo.decoding = 'async';
  photo.addEventListener('error', () => photo.remove(), { once: true });
  element.append(photo);
}

export function safeReturnPath(value, fallback = '/rooms.html') {
  if (!value || !value.startsWith('/') || value.includes('\\') || /[\u0000-\u001f]/.test(value)) return fallback;
  try {
    const url = new URL(value, window.location.origin);
    if (url.origin === window.location.origin && ['/', '/rooms.html', '/my-bookings.html', '/admin.html'].includes(url.pathname)) {
      return url.pathname + url.search + url.hash;
    }
  } catch { /* Use the default page for malformed return paths. */ }
  return fallback;
}

export function icon(name) {
  const paths = {
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18M8 15h2M14 15h2"/>',
    bookings: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    settings: '<path d="M4 7h16M4 17h16M8 4v6M16 14v6"/>',
    logout: '<path d="M9 4H4v16h5M10 12h11M17 8l4 4-4 4"/>',
    spark: '<path d="m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5Z"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    pin: '<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/>',
    close: '<path d="m6 6 12 12M6 18 18 6"/>',
  };
  return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.spark}</svg>`;
}

export function showMessage(element, text, kind = 'error') {
  if (!element) return;

  element.textContent = text;
  element.className = `message ${kind}`;
  element.hidden = !text;
  element.setAttribute('role', kind === 'error' ? 'alert' : 'status');
}

export function describeError(error) {
  if (error instanceof ApiError) {
    if (Array.isArray(error.detail)) {
      return error.detail.map((item) => `${item.loc?.slice(1).join('.') || 'Запрос'}: ${item.msg}`).join('; ');
    }
    return ERROR_LABELS[error.code] || error.detail || 'Не удалось выполнить запрос';
  }
  return 'Сервер недоступен, попробуйте позже';
}

/** `datetime-local` works in the browser's zone; bookings are sent as explicit instants. */
export function localInputToIso(value) {
  if (!value) return null;
  return new Date(value).toISOString();
}

export function isoToLocalInput(iso) {
  const date = new Date(iso);
  const pad = (number) => String(number).padStart(2, '0');

  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export function formatRange(startsAt, endsAt, timeZone) {
  const options = { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone };
  const start = new Date(startsAt).toLocaleString('ru-RU', options);
  const end = new Date(endsAt).toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit', timeZone });

  return `${start} – ${end}`;
}

export function todayIso(timeZone) {
  const now = new Date();
  if (timeZone) {
    const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now);
    const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
    return `${values.year}-${values.month}-${values.day}`;
  }
  const pad = (number) => String(number).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function shiftDay(day, amount) {
  const date = new Date(`${day}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

export function emptyState(title, description, action = '') {
  return `<div class="empty-state"><span class="empty-symbol" aria-hidden="true">◷</span><h3>${escapeHtml(title)}</h3><p>${escapeHtml(description)}</p>${action}</div>`;
}

const ERROR_LABELS = {
  invalid_credentials: 'Проверьте email и пароль.',
  email_exists: 'Аккаунт с этой почтой уже существует. Попробуйте войти.',
  invalid_code: 'Код не подошёл. Проверьте шесть цифр из письма.',
  code_expired: 'Срок действия кода истёк. Запросите новый.',
  session_expired: 'Сессия подтверждения истекла. Запросите новый код.',
  password_login_unavailable: 'Для этого аккаунта используйте вход через Google.',
  booking_conflict: 'Это время уже занято. Обновите расписание и выберите другой интервал.',
  booking_in_past: 'Это время уже прошло. Выберите будущий слот.',
  outside_working_hours: 'Выберите время в пределах рабочего дня офиса.',
  slot_not_aligned: 'Начало и конец встречи должны совпадать с сеткой расписания.',
  invalid_booking_window: 'Время окончания должно быть позже начала.',
  account_disabled: 'Аккаунт отключён. Обратитесь к администратору.',
};

export const EQUIPMENT_LABELS = {
  projector: 'Проектор',
  tv: 'Телевизор',
  whiteboard: 'Доска',
  conference_phone: 'Конференц-телефон',
  video_camera: 'Камера',
  microphone: 'Микрофон',
  laptop: 'Ноутбук',
  other: 'Другое',
};

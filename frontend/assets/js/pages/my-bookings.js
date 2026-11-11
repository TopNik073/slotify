import { api } from '../api.js';
import { createAutosave } from '../autosave.js';
import { describeError, emptyState, escapeHtml, formatRange, renderAvatar, renderNav, requireAuth, showMessage } from '../ui.js';

const $ = (id) => document.getElementById(id);
const RESPONSES = { needs_action: 'ждём ответа', accepted: 'участвует', declined: 'не участвует', tentative: 'возможно' };
const me = await requireAuth().catch((error) => showMessage($('message'), describeError(error)));
if (me) await start();

async function start() {
  let offices = [];
  let bookings = [];
  const requestedView = new URLSearchParams(location.search).get('view');
  let view = ['upcoming', 'invitations', 'past'].includes(requestedView) ? requestedView : 'upcoming';
  let version = 0;
  $('fullName').value = me.fullName || '';
  $('profile-email').textContent = me.email;
  renderAvatar($('profile-avatar'), me);
  try {
    ({ offices } = await api.offices.list());
    $('office').innerHTML = '<option value="">Не выбран</option>' + offices.map((office) => `<option value="${office.id}">${escapeHtml(office.name)} · ${escapeHtml(office.city)}</option>`).join('');
    if (me.officeId && !offices.some((office) => office.id === me.officeId)) {
      $('office').add(new Option('Текущий офис (недоступен)', me.officeId));
    }
    $('office').value = me.officeId || '';
  } catch (error) {
    $('office').innerHTML = '<option value="">Не удалось загрузить офисы</option>';
    $('office').disabled = true;
    showMessage($('message'), describeError(error));
  }

  const profileSave = createAutosave({
    initial: { fullName: me.fullName || null, officeId: me.officeId || null },
    read: () => ({ fullName: $('fullName').value.trim() || null, officeId: $('office').disabled ? me.officeId || null : $('office').value || null }),
    save: (patch) => api.users.updateMe(patch, { keepalive: true }),
    onSaved: (updated) => {
      Object.assign(me, updated);
      renderNav(me);
      renderAvatar($('profile-avatar'), me);
    },
    onState: (state, error) => {
      const labels = { pending: 'Изменения ожидают сохранения…', saving: 'Сохраняем…', saved: 'Сохранено' };
      $('profile-save-status').textContent = state === 'error' ? `Не удалось сохранить. ${describeError(error)}` : labels[state];
      $('profile-save-status').dataset.state = state;
      $('retry-profile').hidden = state !== 'error';
    },
  });
  $('fullName').addEventListener('input', () => profileSave.schedule());
  $('office').addEventListener('change', () => profileSave.schedule());
  $('profile-form').addEventListener('submit', (event) => { event.preventDefault(); void profileSave.flush(); });
  $('retry-profile').addEventListener('click', () => { void profileSave.flush(); });
  if (profileSave.isDirty) profileSave.schedule();
  window.addEventListener('pagehide', () => { if (profileSave.isDirty) void profileSave.flush(); });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden' && profileSave.isDirty) void profileSave.flush();
  });
  document.addEventListener('click', async (event) => {
    const link = event.target.closest('a[href]');
    if (!link || !profileSave.isDirty || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
    const destination = new URL(link.href);
    if (destination.origin !== location.origin || destination.href === location.href) return;
    event.preventDefault();
    if (await profileSave.flush()) window.location.assign(destination.href);
  });

  function renderCalendarStatus(connected) {
    $('calendar-status').innerHTML = connected
      ? 'Подключён. Встречи автоматически появляются в календаре.<br><button type="button" class="link" id="disconnect" style="margin-top: 10px">Отключить календарь</button>'
      : 'Подключите календарь, чтобы получать встречи и отправлять приглашения.<br><button type="button" class="link" id="connect" style="margin-top: 10px">Подключить Google Calendar ↗</button>';
  }
  renderCalendarStatus(me.googleCalendarConnected);
  $('calendar-status').addEventListener('click', async (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.id === 'disconnect' && !window.confirm('Отключить Google Calendar? Новые встречи перестанут синхронизироваться.')) return;
    button.disabled = true;
    try {
      if (button.id === 'disconnect') {
        await api.auth.disconnectGoogle();
        renderCalendarStatus(false);
        showMessage($('message'), 'Календарь отключён.', 'success');
      } else {
        if (!(await profileSave.flush())) { button.disabled = false; return; }
        const { authorizationUrl } = await api.auth.googleLoginUrl(me.email, location.pathname + location.search + location.hash);
        window.location.href = authorizationUrl;
      }
    } catch (error) { showMessage($('message'), describeError(error)); button.disabled = false; }
  });

  async function loadBookings() {
    const requestVersion = ++version;
    $('bookings').innerHTML = emptyState('Собираем ваши планы…', 'Загружаем встречи и приглашения.');
    try {
      const result = await api.bookings.list({ startsAfter: '1970-01-01T00:00:00Z', includeCancelled: $('include-cancelled').checked });
      if (requestVersion !== version) return;
      bookings = result.bookings;
      renderBookings();
    } catch (error) {
      if (requestVersion !== version) return;
      $('bookings').innerHTML = emptyState('Не удалось загрузить встречи', 'Нажмите на кнопку обновления, чтобы попробовать ещё раз.');
      showMessage($('message'), describeError(error));
    }
  }
  function mine(booking) { return booking.participants.find((participant) => participant.userId === me.id || participant.email.toLowerCase() === me.email.toLowerCase()); }
  function isPending(booking) { return booking.organizerId !== me.id && mine(booking)?.response === 'needs_action' && booking.status === 'active' && new Date(booking.endsAt) > new Date(); }
  function renderBookings() {
    const now = new Date();
    const filtered = bookings.filter((booking) => view === 'invitations' ? isPending(booking) : view === 'past' ? new Date(booking.endsAt) <= now : new Date(booking.endsAt) > now);
    filtered.sort((a, b) => view === 'past' ? new Date(b.startsAt) - new Date(a.startsAt) : new Date(a.startsAt) - new Date(b.startsAt));
    $('booking-count').textContent = ` / ${filtered.length}`;
    const invitations = bookings.filter(isPending).length;
    $('invitation-count').textContent = invitations ? `(${invitations})` : '';
    $('bookings').innerHTML = filtered.length ? filtered.map(renderBooking).join('') : emptyState(view === 'invitations' ? 'Все приглашения разобраны' : view === 'past' ? 'История пока пуста' : 'Впереди — свободное время', view === 'invitations' ? 'Здесь появятся встречи, на которые вас пригласили коллеги.' : view === 'past' ? 'Здесь будут встречи, которые уже завершились.' : 'Выберите переговорную и забронируйте время для команды.', view === 'upcoming' ? '<a class="button secondary" href="/rooms.html">Открыть расписание ↗</a>' : '');
  }
  function renderBooking(booking) {
    const timeZone = offices.find((office) => office.id === booking.officeId)?.timezone || 'UTC';
    const date = new Date(booking.startsAt);
    const ongoing = booking.status === 'active' && new Date(booking.endsAt) > new Date();
    const organizer = booking.organizerId === me.id;
    const dateParts = (options) => date.toLocaleDateString('ru-RU', { ...options, timeZone });
    const actions = [];
    if (ongoing && (organizer || me.role === 'admin')) {
      actions.push(`<button type="button" class="danger" data-cancel="${booking.id}">Отменить встречу</button>`);
      if (booking.seriesId) actions.push(`<button type="button" class="danger" data-cancel="${booking.id}" data-series="1">Отменить серию</button>`);
    }
    if (ongoing && !organizer && mine(booking)) {
      if (mine(booking).response !== 'accepted') actions.push(`<button type="button" class="secondary" data-respond="${booking.id}" data-answer="accepted">Буду участвовать</button>`);
      if (mine(booking).response !== 'declined') actions.push(`<button type="button" class="secondary" data-respond="${booking.id}" data-answer="declined">Не смогу</button>`);
    }
    return `<article class="booking-item"><div class="booking-day"><strong>${dateParts({ day: '2-digit' })}</strong><span>${dateParts({ month: 'short' })}</span><br><span>${dateParts({ year: 'numeric' })}</span></div><div><h3 class="booking-title">${escapeHtml(booking.title)}</h3><p class="booking-time">${formatRange(booking.startsAt, booking.endsAt, timeZone)} · ${escapeHtml(timeZone)}</p><p class="muted" style="margin-bottom: 8px">${booking.room ? escapeHtml(booking.room.name) : 'Только оборудование'}${booking.equipment.length ? ` · ${booking.equipment.map((item) => escapeHtml(item.name)).join(', ')}` : ''}</p>${booking.description ? `<p style="font-size: 13px">${escapeHtml(booking.description)}</p>` : ''}<div class="chip-list">${booking.status === 'cancelled' ? '<span class="tag cancelled">Отменена</span>' : ''}${booking.seriesId ? '<span class="tag">Повторяется</span>' : ''}${booking.calendarSynced ? '<span class="tag">Google Calendar</span>' : ''}${booking.participants.map((participant) => `<span class="tag">${escapeHtml(participant.email)} · ${participant.isOrganizer ? 'организатор' : RESPONSES[participant.response] || 'приглашён'}</span>`).join('')}</div>${actions.length ? `<div class="booking-actions">${actions.join('')}</div>` : ''}</div></article>`;
  }
  $('bookings').addEventListener('click', async (event) => {
    const button = event.target.closest('button');
    if (!button || button.disabled) return;
    if (button.dataset.cancel) {
      const wholeSeries = button.dataset.series === '1';
      if (!window.confirm(wholeSeries ? 'Отменить все будущие встречи этой серии?' : 'Отменить эту встречу?')) return;
      button.disabled = true;
      try {
        const result = await api.bookings.cancel(button.dataset.cancel, wholeSeries);
        showMessage($('message'), `Отменено встреч: ${result.cancelled}.`, 'success');
        await loadBookings();
      } catch (error) { showMessage($('message'), describeError(error)); button.disabled = false; }
    } else if (button.dataset.respond) {
      button.disabled = true;
      try {
        await api.bookings.respond(button.dataset.respond, button.dataset.answer);
        showMessage($('message'), 'Ответ на приглашение сохранён.', 'success');
        await loadBookings();
      } catch (error) { showMessage($('message'), describeError(error)); button.disabled = false; }
    }
  });
  document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => {
    view = button.dataset.view;
    const url = new URL(location.href);
    url.searchParams.set('view', view);
    history.replaceState(null, '', url.pathname + url.search + url.hash);
    document.querySelectorAll('[data-view]').forEach((item) => { item.classList.toggle('active', item === button); item.setAttribute('aria-pressed', String(item === button)); });
    renderBookings();
  }));
  document.querySelectorAll('[data-view]').forEach((button) => {
    button.classList.toggle('active', button.dataset.view === view);
    button.setAttribute('aria-pressed', String(button.dataset.view === view));
  });
  $('include-cancelled').addEventListener('change', loadBookings);
  $('reload').addEventListener('click', loadBookings);
  await loadBookings();
}

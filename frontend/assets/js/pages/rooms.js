import { api } from '../api.js';
import {
  EQUIPMENT_LABELS, describeError, emptyState, escapeHtml, formatRange,
  icon, requireAuth, shiftDay, showMessage, todayIso,
} from '../ui.js';

const $ = (id) => document.getElementById(id);
const me = await requireAuth().catch((error) => showMessage($('message'), describeError(error)));
if (me) await start();

async function start() {
  const dialog = $('booking-dialog');
  const participants = new Map();
  let offices = [];
  let availability = null;
  let selection = null;
  let weekStart = null;
  let availabilityVersion = 0;
  let equipmentVersion = 0;
  let searchVersion = 0;
  let searchTimer;
  let submitting = false;
  let roomDetails = null;
  let roomDetailsVersion = 0;
  const office = () => offices.find((item) => item.id === $('office').value);
  const time = (iso) => new Date(iso).toLocaleTimeString('ru-RU', {
    hour: '2-digit', minute: '2-digit', timeZone: office().timezone,
  });
  const message = (text, kind) => showMessage($('booking-message'), text, kind);

  try {
    ({ offices } = await api.offices.list());
    $('office').innerHTML = offices.map((item) => `<option value="${item.id}">${escapeHtml(item.name)} · ${escapeHtml(item.city)}</option>`).join('');
    if (offices.some((item) => item.id === me.officeId)) $('office').value = me.officeId;
  } catch (error) {
    showMessage($('message'), describeError(error));
    $('office').innerHTML = '<option value="">Не удалось загрузить офисы</option>';
  }

  function syncOffice(resetDay = false) {
    const current = office();
    if (!current) {
      $('grid-state').innerHTML = emptyState('Пока нет офисов', 'Администратор может добавить офис и переговорные в разделе «Управление».');
      $('reload').disabled = true;
      return;
    }
    const today = todayIso(current.timezone);
    $('day').min = today;
    $('day').max = shiftDay(today, current.bookingHorizonDays);
    if (resetDay || !$('day').value) $('day').value = today;
    $('office-hint').innerHTML = `${icon('pin')}<span>${escapeHtml(current.address || current.city)} · ${escapeHtml(current.timezone)} · ${current.opensAt.slice(0, 5)}–${current.closesAt.slice(0, 5)}</span>`;
    $('timezone-label').textContent = current.timezone;
    updateWeekStart();
  }

  function updateWeekStart() {
    const day = $('day').value;
    const weekday = new Date(`${day}T12:00:00Z`).getUTCDay() || 7;
    weekStart = shiftDay(day, 1 - weekday);
    renderWeek();
  }

  function renderWeek() {
    if (!weekStart || !office()) return;
    const today = todayIso(office().timezone);
    const selected = $('day').value;
    const format = (day, options) => new Date(`${day}T12:00:00Z`).toLocaleDateString('ru-RU', { ...options, timeZone: 'UTC' });
    $('week-title').textContent = format(weekStart, { day: 'numeric', month: 'long' }) + ' — ' + format(shiftDay(weekStart, 6), { day: 'numeric', month: 'long' });
    $('week').innerHTML = Array.from({ length: 7 }, (_, index) => {
      const day = shiftDay(weekStart, index);
      const closed = !office().workdays.includes(index + 1);
      const disabled = day < $('day').min || day > $('day').max;
      return `<button type="button" data-day="${day}" class="day-button ${day === selected ? 'active' : ''}" aria-pressed="${day === selected}" aria-label="${format(day, { day: 'numeric', month: 'long', weekday: 'long' })}${closed ? ', выходной' : ''}" ${disabled ? 'disabled' : ''}><span>${format(day, { weekday: 'short' })}</span><strong>${Number(day.slice(-2))}</strong><small>${day === today ? 'Сегодня' : closed ? 'Выходной' : ''}</small></button>`;
    }).join('');
    $('prev-week').disabled = shiftDay(weekStart, -1) < $('day').min;
    $('next-week').disabled = shiftDay(weekStart, 7) > $('day').max;
  }

  async function loadAvailability({ keepMessage = false } = {}) {
    if (!office() || !$('filters').reportValidity()) return;
    const version = ++availabilityVersion;
    if (!keepMessage) showMessage($('message'), '');
    availability = null;
    resetSelection();
    $('grid').hidden = true;
    $('grid-state').innerHTML = emptyState('Смотрим расписание…', 'Проверяем свободное время для вашего офиса.');
    $('schedule').setAttribute('aria-busy', 'true');
    try {
      const result = await api.rooms.availability(office().id, $('day').value, $('capacity').value || undefined);
      if (version !== availabilityVersion) return;
      availability = result;
      renderGrid();
    } catch (error) {
      if (version !== availabilityVersion) return;
      $('grid-state').innerHTML = emptyState('Расписание не загрузилось', 'Попробуйте обновить его ещё раз.');
      showMessage($('message'), describeError(error));
    } finally {
      if (version === availabilityVersion) $('schedule').removeAttribute('aria-busy');
    }
  }

  function renderGrid() {
    const rooms = availability.rooms;
    if (!rooms.length || !rooms[0].slots.length) {
      $('grid').hidden = true;
      const closed = !office().workdays.includes(new Date(`${$('day').value}T12:00:00Z`).getUTCDay() || 7);
      $('grid-state').innerHTML = emptyState(closed ? 'Сегодня офис отдыхает' : 'Подходящих переговорных нет', closed ? 'Выберите рабочий день в календаре выше.' : 'Попробуйте уменьшить число участников или выбрать другой офис.');
      return;
    }
    $('grid-state').innerHTML = '';
    $('grid').hidden = false;
    const slots = rooms[0].slots;
    $('grid').style.minWidth = `${180 + slots.length * 43}px`;
    $('grid').querySelector('thead').innerHTML = `<tr><th class="room-label" scope="col">Комната / время</th>${slots.map((slot) => `<th scope="col">${time(slot.startsAt)}</th>`).join('')}</tr>`;
    $('grid').querySelector('tbody').innerHTML = rooms.map(({ room, slots }, roomIndex) => `<tr><th class="room-label" scope="row"><button type="button" class="room-info-trigger" data-room-details="${room.id}" aria-haspopup="dialog" aria-label="О переговорной ${escapeHtml(room.name)}"><span class="room-number">${String(roomIndex + 1).padStart(2, '0')}</span><strong class="room-name">${escapeHtml(room.name)}</strong><span class="room-meta">до ${room.capacity} чел.${room.floor ? ` · этаж ${escapeHtml(room.floor)}` : ''}</span><span class="room-info-hint">О комнате ↗</span></button></th>${slots.map((slot, index) => {
      const past = new Date(slot.startsAt) <= new Date();
      const mine = !slot.isFree && slot.isMine;
      const label = `${room.name}, ${time(slot.startsAt)}–${time(slot.endsAt)}, ${mine ? 'ваша встреча' : slot.isFree ? 'свободно' : 'занято'}${past ? ', время прошло' : ''}`;
      return `<td><button type="button" class="slot ${past ? 'past' : ''} ${mine ? 'mine' : ''}" data-room="${room.id}" data-index="${index}" ${bookable(slot) ? '' : 'disabled'} aria-label="${escapeHtml(label)}" title="${escapeHtml(label)}">${mine ? '<span aria-hidden="true">✓</span>' : ''}</button></td>`;
    }).join('')}</tr>`).join('');
  }

  function bookable(slot) { return slot.isFree && new Date(slot.startsAt) > new Date(); }

  function addressLabel(current) {
    return current.address ? [current.city, current.address].filter(Boolean).join(', ') : `${current.city} · адрес офиса не указан`;
  }

  async function openRoomDetails(roomId) {
    const entry = availability?.rooms.find(({ room }) => room.id === roomId);
    if (!entry) return;
    roomDetails = entry.room;
    const current = availability.office;
    $('room-heading').textContent = roomDetails.name;
    $('room-address').textContent = addressLabel(current);
    $('room-floor').textContent = roomDetails.floor ? `Этаж: ${roomDetails.floor}` : 'Этаж не указан';
    $('room-location-icon').innerHTML = icon('pin');
    $('room-office').textContent = current.name;
    $('room-capacity').textContent = `До ${roomDetails.capacity} человек`;
    $('room-description').textContent = roomDetails.description?.trim() || 'Описание и ориентиры пока не добавлены. Уточните расположение комнаты у администратора офиса.';
    $('room-choose-time').disabled = !entry.slots.some(bookable);
    $('room-choose-time').textContent = entry.slots.some(bookable) ? 'Выбрать время ↗' : 'На выбранную дату свободного времени нет';
    $('room-dialog').showModal();
    await loadRoomEquipment();
  }

  async function loadRoomEquipment() {
    const version = ++roomDetailsVersion;
    const room = roomDetails;
    if (!room) return;
    $('room-equipment').innerHTML = '<p class="muted">Загружаем оборудование…</p>';
    try {
      const { equipment } = await api.equipment.list({ officeId: room.officeId, roomId: room.id });
      if (version !== roomDetailsVersion || !roomDetails) return;
      const fixed = equipment.filter((item) => !item.isMovable && item.homeRoomId === room.id);
      $('room-equipment').innerHTML = fixed.length
        ? `<ul class="room-equipment">${fixed.map((item) => `<li>${escapeHtml(item.name)} <span class="muted">· ${EQUIPMENT_LABELS[item.type] || 'Другое'}</span></li>`).join('')}</ul><p class="muted">Доступность на время встречи проверим при бронировании.</p>`
        : '<p class="muted">Закреплённое оборудование не указано. Переносное можно добавить при бронировании.</p>';
    } catch (error) {
      if (version !== roomDetailsVersion || !roomDetails) return;
      $('room-equipment').innerHTML = `<p class="muted">${escapeHtml(describeError(error))}</p><button type="button" class="secondary" id="retry-room-equipment">Повторить загрузку</button>`;
    }
  }

  $('room-equipment').addEventListener('click', (event) => {
    if (event.target.closest('#retry-room-equipment')) loadRoomEquipment();
  });
  $('close-room').addEventListener('click', () => $('room-dialog').close());
  $('room-dialog').addEventListener('close', () => { roomDetails = null; ++roomDetailsVersion; });
  $('room-choose-time').addEventListener('click', () => {
    const roomId = roomDetails?.id;
    const slot = [...$('grid').querySelectorAll('.slot:not(:disabled)')].find((button) => button.dataset.room === roomId);
    $('room-dialog').close();
    if (slot) {
      slot.focus({ preventScroll: true });
      slot.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'auto' });
    }
  });
  function selectedEntry() { return availability?.rooms.find(({ room }) => room.id === selection?.roomId); }
  function selectedWindow() {
    const entry = selectedEntry();
    return { room: entry.room, startsAt: entry.slots[selection.startIndex].startsAt, endsAt: entry.slots[selection.endIndex].endsAt };
  }

  function resetSelection() {
    ++equipmentVersion;
    ++searchVersion;
    clearTimeout(searchTimer);
    selection = null;
    if (dialog.open) dialog.close();
    highlightSelection();
  }

  function highlightSelection() {
    $('grid').querySelectorAll('.slot').forEach((button) => {
      button.classList.toggle('selected', Boolean(selection && button.dataset.room === selection.roomId && Number(button.dataset.index) >= selection.startIndex && Number(button.dataset.index) <= selection.endIndex));
    });
  }

  function allowedEnds(startIndex) {
    const entry = selectedEntry();
    const values = [];
    for (let index = startIndex; index < entry.slots.length; index++) {
      if (!bookable(entry.slots[index])) break;
      const duration = (index - startIndex + 1) * office().slotMinutes;
      if (duration > office().maxBookingMinutes) break;
      if (duration >= office().minBookingMinutes) values.push(index);
    }
    return values;
  }

  function renderTimeOptions(preferredEnd) {
    const entry = selectedEntry();
    $('starts-at').innerHTML = entry.slots.map((slot, index) => `<option value="${index}" ${!bookable(slot) || !allowedEnds(index).length ? 'disabled' : ''}>${time(slot.startsAt)}</option>`).join('');
    $('starts-at').value = selection.startIndex;
    const ends = allowedEnds(selection.startIndex);
    $('ends-at').innerHTML = ends.map((index) => `<option value="${index}">${time(entry.slots[index].endsAt)}</option>`).join('');
    selection.endIndex = ends.includes(preferredEnd) ? preferredEnd : ends[0];
    $('ends-at').value = selection.endIndex;
    syncWindow();
  }

  function syncWindow() {
    const { room, startsAt, endsAt } = selectedWindow();
    const duration = (new Date(endsAt) - new Date(startsAt)) / 60000;
    $('selection-summary').textContent = `${room.name} · ${formatRange(startsAt, endsAt, office().timezone)} · ${duration} мин`;
    $('booking-location').textContent = `${addressLabel(availability.office)} · ${room.floor ? `этаж ${room.floor}` : 'этаж не указан'}`;
    document.querySelectorAll('[data-duration]').forEach((button) => {
      button.classList.toggle('active', Number(button.dataset.duration) === duration);
      const endIndex = selection.startIndex + Number(button.dataset.duration) / office().slotMinutes - 1;
      button.disabled = !Number.isInteger(endIndex) || !allowedEnds(selection.startIndex).includes(endIndex);
    });
    highlightSelection();
    loadEquipment();
  }

  async function loadEquipment() {
    const version = ++equipmentVersion;
    const { room, startsAt, endsAt } = selectedWindow();
    const checked = new Set([...$('equipment').querySelectorAll('input:checked')].map((input) => input.value));
    $('submit').disabled = true;
    $('equipment').innerHTML = '<p class="muted">Проверяем доступность…</p>';
    try {
      const { equipment } = await api.equipment.free(office().id, startsAt, endsAt, room.id);
      if (version !== equipmentVersion || !selection) return;
      $('equipment').innerHTML = equipment.length ? equipment.map((item) => `<label><input type="checkbox" value="${item.id}" ${checked.has(item.id) ? 'checked' : ''} />${escapeHtml(item.name)}<span class="muted">${EQUIPMENT_LABELS[item.type] || 'Другое'}${item.isMovable ? '' : ' · в комнате'}</span></label>`).join('') : '<p class="muted">На это время свободного оборудования нет. Комнату можно забронировать отдельно.</p>';
      $('submit').disabled = false;
    } catch (error) {
      if (version !== equipmentVersion || !selection) return;
      $('equipment').innerHTML = `<p class="muted">${escapeHtml(describeError(error))}</p><button type="button" class="secondary" id="retry-equipment">Повторить проверку</button>`;
    }
  }

  $('equipment').addEventListener('click', (event) => { if (event.target.closest('#retry-equipment')) loadEquipment(); });
  $('grid').addEventListener('click', (event) => {
    const roomButton = event.target.closest('[data-room-details]');
    if (roomButton) { openRoomDetails(roomButton.dataset.roomDetails); return; }
    const button = event.target.closest('button[data-room]');
    if (!button || button.disabled || submitting) return;
    selection = { roomId: button.dataset.room, startIndex: Number(button.dataset.index), endIndex: Number(button.dataset.index) };
    if (!allowedEnds(selection.startIndex).length) {
      selection = null;
      showMessage($('message'), `Для этой комнаты нужна непрерывная бронь от ${office().minBookingMinutes} мин. Выберите другое начало.`);
      return;
    }
    $('booking-form').reset();
    $('recurrence-options').hidden = true;
    participants.clear();
    $('participants').innerHTML = $('search-results').innerHTML = '';
    message('');
    renderTimeOptions();
    dialog.showModal();
    $('title').focus();
  });
  $('starts-at').addEventListener('change', () => { selection.startIndex = Number($('starts-at').value); renderTimeOptions(); });
  $('ends-at').addEventListener('change', () => { selection.endIndex = Number($('ends-at').value); syncWindow(); });
  document.querySelectorAll('[data-duration]').forEach((button) => button.addEventListener('click', () => {
    selection.endIndex = selection.startIndex + Number(button.dataset.duration) / office().slotMinutes - 1;
    $('ends-at').value = selection.endIndex;
    syncWindow();
  }));
  $('cancel-selection').addEventListener('click', () => { if (!submitting) resetSelection(); });
  dialog.addEventListener('cancel', (event) => { if (submitting) event.preventDefault(); });
  dialog.addEventListener('close', () => { selection = null; ++equipmentVersion; ++searchVersion; clearTimeout(searchTimer); highlightSelection(); });
  $('frequency').addEventListener('change', () => { $('recurrence-options').hidden = !$('frequency').value; $('count').required = Boolean($('frequency').value); });

  function renderParticipants() {
    $('participants').innerHTML = [...participants].map(([email, entry]) => `<span class="tag">${escapeHtml(entry.label)}<button type="button" class="link" data-remove="${escapeHtml(email)}" aria-label="Удалить ${escapeHtml(entry.label)}">×</button></span>`).join('');
  }
  $('participants').addEventListener('click', (event) => {
    const email = event.target.dataset.remove;
    if (!email) return;
    participants.delete(email);
    $('search-results').querySelectorAll('input').forEach((input) => { if (input.dataset.email === email) input.checked = false; });
    renderParticipants();
  });
  $('participant-search').addEventListener('input', () => {
    clearTimeout(searchTimer);
    const version = ++searchVersion;
    const query = $('participant-search').value.trim();
    $('search-results').innerHTML = '';
    if (query.length < 2) return;
    searchTimer = setTimeout(async () => {
      try {
        const { users } = await api.users.search(query);
        if (version !== searchVersion) return;
        const others = users.filter((user) => user.id !== me.id);
        $('search-results').innerHTML = others.length ? others.map((user) => `<label><input type="checkbox" data-user="${user.id}" data-email="${escapeHtml(user.email.toLowerCase())}" data-label="${escapeHtml(user.fullName || user.email)}" ${participants.has(user.email.toLowerCase()) ? 'checked' : ''} />${escapeHtml(user.fullName || user.email)}<span class="muted">${escapeHtml(user.email)}</span></label>`).join('') : '<p class="muted">Коллегу не нашли. Его можно пригласить по почте.</p>';
      } catch (error) { if (version === searchVersion) $('search-results').innerHTML = `<p class="muted">${escapeHtml(describeError(error))}</p>`; }
    }, 250);
  });
  $('search-results').addEventListener('change', (event) => {
    const input = event.target;
    if (!input.dataset.user) return;
    if (input.checked) participants.set(input.dataset.email, { userId: input.dataset.user, label: input.dataset.label });
    else participants.delete(input.dataset.email);
    renderParticipants();
  });
  $('add-email').addEventListener('click', () => {
    const input = $('participant-email');
    const email = input.value.trim().toLowerCase();
    if (!email || !input.reportValidity()) { message('Введите корректный email гостя.'); return; }
    if (email === me.email.toLowerCase()) { message('Вы уже организатор этой встречи.'); return; }
    if (!participants.has(email)) participants.set(email, { userId: null, label: email });
    input.value = '';
    message('');
    renderParticipants();
  });

  $('booking-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!selection || submitting || $('submit').disabled) return;
    if (!$('title').value.trim()) { message('Добавьте название встречи.'); $('title').focus(); return; }
    if ($('participant-email').value.trim()) { message('Нажмите «Добавить», чтобы включить гостя в список участников.'); return; }
    const { room, startsAt, endsAt } = selectedWindow();
    if (new Date(startsAt) <= new Date()) { message('Выбранное время уже прошло. Обновите расписание.'); return; }
    const frequency = $('frequency').value;
    const payload = {
      title: $('title').value.trim(), description: $('description').value.trim() || null,
      startsAt, endsAt, roomId: room.id,
      equipmentIds: [...$('equipment').querySelectorAll('input:checked')].map((input) => input.value),
      participantUserIds: [...participants.values()].filter((entry) => entry.userId).map((entry) => entry.userId),
      participantEmails: [...participants].filter(([, entry]) => !entry.userId).map(([email]) => email),
      recurrence: frequency ? { frequency, interval: Number($('interval').value), count: Number($('count').value) } : null,
    };
    submitting = true;
    message('');
    const fields = [...$('booking-form').elements];
    const disabled = fields.map((field) => field.disabled);
    fields.forEach((field) => { field.disabled = true; });
    $('cancel-selection').disabled = true;
    $('submit').textContent = 'Бронируем…';
    try {
      const result = await api.bookings.create(payload);
      const allSynced = result.occurrences.every((item) => item.calendarSynced);
      resetSelection();
      await loadAvailability({ keepMessage: true });
      showMessage($('message'), `Готово! ${result.occurrences.length === 1 ? 'Встреча забронирована.' : `Создано встреч: ${result.occurrences.length}.`}${allSynced ? ' Приглашения отправлены через Google Calendar.' : ' Синхронизация с Google Calendar не выполнена. Бронь сохранена.'}`, 'success');
    } catch (error) { message(describeError(error)); }
    finally {
      submitting = false;
      fields.forEach((field, index) => { field.disabled = disabled[index]; });
      $('cancel-selection').disabled = false;
      $('submit').innerHTML = 'Забронировать <span aria-hidden="true">↗</span>';
    }
  });

  $('filters').addEventListener('submit', (event) => { event.preventDefault(); loadAvailability(); });
  $('office').addEventListener('change', () => { syncOffice(true); loadAvailability(); });
  $('day').addEventListener('change', () => { if ($('day').checkValidity() && $('day').value) { updateWeekStart(); loadAvailability(); } });
  $('capacity').addEventListener('change', () => loadAvailability());
  $('week').addEventListener('click', (event) => { const button = event.target.closest('[data-day]'); if (!button || button.disabled) return; $('day').value = button.dataset.day; renderWeek(); loadAvailability(); });
  $('prev-week').addEventListener('click', () => { weekStart = shiftDay(weekStart, -7); renderWeek(); });
  $('next-week').addEventListener('click', () => { weekStart = shiftDay(weekStart, 7); renderWeek(); });
  $('today').addEventListener('click', () => { if (!office()) return; $('day').value = todayIso(office().timezone); updateWeekStart(); loadAvailability(); });
  syncOffice(true);
  if (office()) await loadAvailability();
}

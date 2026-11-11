import { api } from './api.js';
import { EQUIPMENT_LABELS, describeError, escapeHtml, showMessage } from './ui.js';
import { attachTimezonePicker } from './timezones.js';

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const TYPES = {
  office: { title: 'Редактировать офис', save: api.admin.updateOffice },
  room: { title: 'Редактировать комнату', save: api.admin.updateRoom },
  equipment: { title: 'Редактировать оборудование', save: api.admin.updateEquipment },
  user: { title: 'Редактировать пользователя', save: api.admin.updateUser },
};

export function createRecordEditor({ me, getOffices, getRooms, onSaved }) {
  const dialog = document.getElementById('record-editor');
  const form = dialog.querySelector('form');
  const body = document.getElementById('record-fields');
  const message = document.getElementById('record-message');
  let current = null;
  let fields = [];
  let saving = false;

  function configuration(type, record) {
    const name = { key: 'name', label: 'Название', required: true, max: 255 };
    const description = { key: 'description', label: type === 'room' ? 'Описание и ориентиры' : 'Описание', type: 'textarea', nullable: true,
      placeholder: type === 'room' ? 'Номер кабинета, корпус, как пройти от входа и особенности комнаты' : '' };
    const active = { key: 'isActive', label: 'Доступно для бронирования', type: 'checkbox' };
    if (type === 'office') return [
      name, { key: 'city', label: 'Город', required: true, max: 255 },
      { key: 'address', label: 'Адрес', nullable: true, max: 512 },
      { key: 'timezone', label: 'Часовой пояс', required: true, type: 'timezone' },
      { key: 'opensAt', label: 'Открытие', type: 'time', required: true },
      { key: 'closesAt', label: 'Закрытие', type: 'time', required: true },
      { key: 'slotMinutes', label: 'Шаг расписания, мин', type: 'number', min: 5, max: 240 },
      { key: 'minBookingMinutes', label: 'Минимальная бронь, мин', type: 'number', min: 5 },
      { key: 'maxBookingMinutes', label: 'Максимальная бронь, мин', type: 'number', min: 5 },
      { key: 'bookingHorizonDays', label: 'Бронирование вперёд, дней', type: 'number', min: 1, max: 730 },
      { key: 'workdays', label: 'Рабочие дни', type: 'weekdays' }, active,
    ];
    if (type === 'room') return [name, { key: 'capacity', label: 'Вместимость', type: 'number', min: 1, max: 1000 }, { key: 'floor', label: 'Этаж', nullable: true, max: 32 }, description, active];
    if (type === 'equipment') return [
      name, { key: 'type', label: 'Тип', type: 'select', options: Object.entries(EQUIPMENT_LABELS) },
      { key: 'inventoryNumber', label: 'Инвентарный номер', nullable: true, max: 64 }, description,
      { key: 'homeRoomId', label: 'Закреплено за комнатой', type: 'select', nullable: true,
        options: [['', 'Не закреплено'], ...getRooms().filter((room) => room.officeId === record.officeId).map((room) => [room.id, room.name])] },
      { key: 'isMovable', label: 'Можно переносить в другие комнаты', type: 'checkbox' }, active,
    ];
    return [
      { key: 'fullName', label: 'Имя', nullable: true, max: 255 },
      { key: 'officeId', label: 'Офис', type: 'select', nullable: true, options: [['', 'Не выбран'], ...getOffices().map((office) => [office.id, office.name])] },
      { key: 'role', label: 'Роль', type: 'select', disabled: record.id === me.id, options: [['user', 'Пользователь'], ['admin', 'Администратор']] },
      { key: 'status', label: 'Статус', type: 'select', disabled: record.id === me.id, options: [['active', 'Активен'], ['invited', 'Приглашён'], ['disabled', 'Отключён']] },
    ];
  }

  function renderField(field, record) {
    const id = `edit-${field.key}`;
    const value = record[field.key] ?? '';
    const attributes = `${field.required || field.type === 'number' ? 'required' : ''} ${field.disabled ? 'disabled' : ''}`;
    const label = `<label for="${id}">${field.label}</label>`;
    if (field.type === 'checkbox') return `<div class="field"><label class="checkbox-label"><input type="checkbox" id="${id}" ${value ? 'checked' : ''} />${field.label}</label></div>`;
    if (field.type === 'weekdays') return `<fieldset class="field"><legend>${field.label}</legend><div class="weekday-picker">${WEEKDAYS.map((day, index) => `<label><input type="checkbox" name="workdays" value="${index + 1}" ${value.includes(index + 1) ? 'checked' : ''} />${day}</label>`).join('')}</div></fieldset>`;
    if (field.type === 'textarea') return `<div class="field">${label}<textarea id="${id}" rows="3" placeholder="${escapeHtml(field.placeholder || '')}">${escapeHtml(value)}</textarea></div>`;
    if (field.type === 'select') return `<div class="field">${label}<select id="${id}" ${attributes}>${field.options.map(([key, text]) => `<option value="${escapeHtml(key)}" ${key === value ? 'selected' : ''}>${escapeHtml(text)}</option>`).join('')}</select></div>`;
    return `<div class="field">${label}<input id="${id}" type="${field.type === 'timezone' ? 'text' : field.type || 'text'}" value="${escapeHtml(field.type === 'time' ? value.slice(0, 5) : value)}" ${attributes} ${field.max ? `${field.type === 'number' ? 'max' : 'maxlength'}="${field.max}"` : ''} ${field.min ? `min="${field.min}"` : ''} /></div>`;
  }

  async function open(type, record) {
    if (saving || !record) return;
    current = { type, record };
    fields = configuration(type, record);
    document.getElementById('record-title').textContent = TYPES[type].title;
    document.getElementById('record-caption').textContent = type === 'user' ? record.email : record.name;
    showMessage(message, '');
    body.innerHTML = fields.map((field) => renderField(field, record)).join('');
    dialog.showModal();
    body.querySelector('input, select, textarea')?.focus();
    if (type === 'office') {
      try { await attachTimezonePicker(document.getElementById('edit-timezone')); }
      catch (error) { showMessage(message, describeError(error)); }
    }
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!current || saving) return;
    const payload = {};
    for (const field of fields) {
      if (field.disabled) continue;
      if (field.type === 'weekdays') {
        payload[field.key] = [...form.querySelectorAll('[name="workdays"]:checked')].map((input) => Number(input.value));
        if (!payload[field.key].length) { showMessage(message, 'Выберите хотя бы один рабочий день.'); return; }
        continue;
      }
      const input = document.getElementById(`edit-${field.key}`);
      payload[field.key] = field.type === 'checkbox' ? input.checked : field.type === 'number' ? Number(input.value) : input.value.trim() || (field.nullable ? null : '');
    }
    if (current.type === 'office' && (payload.opensAt >= payload.closesAt || payload.minBookingMinutes > payload.maxBookingMinutes)) {
      showMessage(message, 'Проверьте часы работы и ограничения длительности брони.'); return;
    }
    saving = true;
    const controls = [...form.elements];
    const wasDisabled = controls.map((input) => input.disabled);
    controls.forEach((input) => { input.disabled = true; });
    document.getElementById('record-close').disabled = true;
    showMessage(message, '');
    try {
      const result = await TYPES[current.type].save(current.record.id, payload);
      await onSaved(current.type, result);
      dialog.close();
    } catch (error) { showMessage(message, describeError(error)); }
    finally {
      saving = false;
      controls.forEach((input, index) => { input.disabled = wasDisabled[index]; });
      document.getElementById('record-close').disabled = false;
    }
  });
  dialog.querySelectorAll('[data-close-editor]').forEach((button) => button.addEventListener('click', () => { if (!saving) dialog.close(); }));
  dialog.addEventListener('cancel', (event) => { if (saving) event.preventDefault(); });
  return { open };
}

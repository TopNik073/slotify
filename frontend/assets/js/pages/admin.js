import { api } from '/assets/js/api.js';
import { EQUIPMENT_LABELS, describeError, escapeHtml, renderNav, requireAuth, showMessage } from '/assets/js/ui.js';
import { createRecordEditor } from '../admin-editor.js';
import { attachTimezonePicker } from '../timezones.js';

const me = await requireAuth({ adminOnly: true }).catch((error) => showMessage(document.getElementById('message'), describeError(error)));
if (me) {
  const message = document.getElementById('message');
  const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  let offices = [];
  let rooms = [];
  let roomCatalog = [];
  let equipmentCatalog = [];
  let userCatalog = [];
  let usersOffset = 0;
  let usersTotal = 0;
  let usersVersion = 0;
  let searchTimer;
  const editor = createRecordEditor({
    me, getOffices: () => offices, getRooms: () => roomCatalog,
    onSaved: async (type, record) => {
      if (type === 'user') {
        if (record.id === me.id) { Object.assign(me, record); renderNav(me); }
        await reloadUsers();
      } else {
        await reloadOffices();
        await reloadRooms();
        await reloadEquipment();
      }
      showMessage(message, 'Изменения сохранены', 'success');
    },
  });
  attachTimezonePicker(document.getElementById('o-tz')).catch((error) => showMessage(message, describeError(error)));

  function renderEquipmentRooms() {
    const officeId = document.getElementById('e-office').value;
    const select = document.getElementById('e-room');
    const selected = select.value;
    select.innerHTML = '<option value="">Не закреплено</option>' + roomCatalog
      .filter((room) => room.officeId === officeId && room.isActive)
      .map((room) => `<option value="${room.id}">${escapeHtml(room.name)}</option>`).join('');
    if (roomCatalog.some((room) => room.id === selected && room.officeId === officeId && room.isActive)) select.value = selected;
  }

  document.querySelectorAll('.tabs button').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.tabs button').forEach((other) => other.classList.remove('active'));
      button.classList.add('active');
      document.querySelectorAll('.tabs button').forEach((other) => other.setAttribute('aria-pressed', String(other === button)));

      document.querySelectorAll('[data-panel]').forEach((panel) => {
        panel.hidden = panel.dataset.panel !== button.dataset.tab;
      });
    });
  });

  document.getElementById('o-workdays').innerHTML = WEEKDAYS.map(
    (label, index) =>
      `<label class="slot" style="cursor: pointer">
        <input type="checkbox" value="${index + 1}" ${index < 5 ? 'checked' : ''} /> ${label}
      </label>`,
  ).join('');

  document.getElementById('e-type').innerHTML = Object.entries(EQUIPMENT_LABELS)
    .map(([value, label]) => `<option value="${value}">${label}</option>`)
    .join('');

  function officeOptions(includeEmpty = false) {
    return (
      (includeEmpty ? '<option value="">Все офисы</option>' : '') +
      offices
        .map((office) => `<option value="${office.id}">${escapeHtml(office.name)}, ${escapeHtml(office.city)}</option>`)
        .join('')
    );
  }

  async function reloadOffices() {
    ({ offices } = await api.offices.list(true));
    for (const id of ['r-office', 'e-office', 'rooms-filter', 'equipment-filter']) {
      const select = document.getElementById(id);
      const previous = select.value;
      select.innerHTML = officeOptions(id.endsWith('filter'));
      if ([...select.options].some((option) => option.value === previous)) select.value = previous;
    }
    renderEquipmentRooms();

    document.getElementById('offices-table').innerHTML = `
      <tr><th>Офис</th><th>Пояс</th><th>Часы</th><th>Слот</th><th>Горизонт</th><th>Статус</th><th></th></tr>
      ${offices
        .map(
          (office) => `
            <tr>
              <td>${escapeHtml(office.name)}<div class="muted">${escapeHtml(office.city)}</div></td>
              <td>${escapeHtml(office.timezone)}</td>
              <td>${office.opensAt.slice(0, 5)}–${office.closesAt.slice(0, 5)}
                <div class="muted">${office.workdays.map((day) => WEEKDAYS[day - 1]).join(' ')}</div>
              </td>
              <td>${office.slotMinutes} мин</td>
              <td>${office.bookingHorizonDays} дн.</td>
              <td>${office.isActive ? 'активен' : 'отключён'}</td>
              <td style="white-space: nowrap">
                <button type="button" class="secondary" data-edit-office="${office.id}">Изменить</button>
                <button type="button" class="secondary" data-toggle-office="${office.id}"
                  data-active="${office.isActive}">${office.isActive ? 'Отключить' : 'Включить'}</button>
                <button type="button" class="danger" data-delete-office="${office.id}">Удалить</button>
              </td>
            </tr>`,
        )
        .join('')}`;
  }

  async function reloadRooms() {
    const officeId = document.getElementById('rooms-filter').value || undefined;
    ({ rooms: roomCatalog } = await api.rooms.list({ includeInactive: true }));
    rooms = roomCatalog.filter((room) => !officeId || room.officeId === officeId);
    renderEquipmentRooms();

    document.getElementById('rooms-table').innerHTML = `
      <tr><th>Комната</th><th>Мест</th><th>Этаж</th><th>Статус</th><th></th></tr>
      ${rooms
        .map(
          (room) => `
            <tr>
              <td>${escapeHtml(room.name)}</td>
              <td>${room.capacity}</td>
              <td>${escapeHtml(room.floor || '—')}</td>
              <td>${room.isActive ? 'активна' : 'отключена'}</td>
              <td style="white-space: nowrap">
                <button type="button" class="secondary" data-edit-room="${room.id}">Изменить</button>
                <button type="button" class="secondary" data-toggle-room="${room.id}"
                  data-active="${room.isActive}">${room.isActive ? 'Отключить' : 'Включить'}</button>
                <button type="button" class="danger" data-delete-room="${room.id}">Удалить</button>
              </td>
            </tr>`,
        )
        .join('')}`;
  }

  async function reloadEquipment() {
    const officeId = document.getElementById('equipment-filter').value || undefined;
    const { equipment } = await api.equipment.list({ officeId, includeInactive: true });
    equipmentCatalog = equipment;

    document.getElementById('equipment-table').innerHTML = `
      <tr><th>Название</th><th>Тип</th><th>Инв. номер</th><th>Привязка</th><th>Статус</th><th></th></tr>
      ${equipment
        .map(
          (item) => `
            <tr>
              <td>${escapeHtml(item.name)}</td>
              <td>${EQUIPMENT_LABELS[item.type] || item.type}</td>
              <td>${escapeHtml(item.inventoryNumber || '—')}</td>
              <td>${
                item.isMovable
                  ? 'переносное'
                  : `закреплено: ${escapeHtml(
                      roomCatalog.find((room) => room.id === item.homeRoomId)?.name || '—',
                    )}`
              }</td>
              <td>${item.isActive ? 'активно' : 'отключено'}</td>
              <td style="white-space: nowrap">
                <button type="button" class="secondary" data-edit-equipment="${item.id}">Изменить</button>
                <button type="button" class="secondary" data-toggle-equipment="${item.id}"
                  data-active="${item.isActive}">${item.isActive ? 'Отключить' : 'Включить'}</button>
                <button type="button" class="danger" data-delete-equipment="${item.id}">Удалить</button>
              </td>
            </tr>`,
        )
        .join('')}`;
  }

  async function reloadUsers() {
    const version = ++usersVersion;
    const limit = Number(document.getElementById('u-limit').value);
    document.getElementById('users-prev').disabled = document.getElementById('users-next').disabled = true;
    const { users, total } = await api.admin.listUsers({
      status: document.getElementById('u-status').value || undefined,
      role: document.getElementById('u-role').value || undefined,
      q: document.getElementById('u-search').value.trim() || undefined,
      limit, offset: usersOffset,
    });
    if (version !== usersVersion) return;
    usersTotal = total;
    if (usersOffset > 0 && usersOffset >= total) {
      usersOffset = total ? Math.floor((total - 1) / limit) * limit : 0;
      return reloadUsers();
    }
    userCatalog = users;
    document.getElementById('users-summary').textContent = total ? `${usersOffset + 1}–${Math.min(usersOffset + users.length, total)} из ${total}` : 'Пользователи не найдены';
    document.getElementById('users-page').textContent = `${Math.floor(usersOffset / limit) + 1} / ${Math.max(1, Math.ceil(total / limit))}`;
    document.getElementById('users-prev').disabled = usersOffset === 0;
    document.getElementById('users-next').disabled = usersOffset + limit >= total;

    document.getElementById('users-table').innerHTML = `
      <tr><th>Пользователь</th><th>Офис</th><th>Роль</th><th>Статус</th><th></th></tr>
      ${users
        .map(
          (user) => `
            <tr>
              <td>${escapeHtml(user.fullName || '—')}<div class="muted">${escapeHtml(user.email)}</div></td>
              <td>${escapeHtml(offices.find((office) => office.id === user.officeId)?.name || '—')}</td>
              <td>
                <select data-role="${user.id}" aria-label="Роль ${escapeHtml(user.email)}" ${user.id === me.id ? 'disabled' : ''}>
                  <option value="user" ${user.role === 'user' ? 'selected' : ''}>Пользователь</option>
                  <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Администратор</option>
                </select>
              </td>
              <td>
                <select data-status="${user.id}" aria-label="Статус ${escapeHtml(user.email)}" ${user.id === me.id ? 'disabled' : ''}>
                  <option value="active" ${user.status === 'active' ? 'selected' : ''}>Активен</option>
                  <option value="invited" ${user.status === 'invited' ? 'selected' : ''}>Приглашён</option>
                  <option value="disabled" ${user.status === 'disabled' ? 'selected' : ''}>Отключён</option>
                </select>
              </td>
              <td><button type="button" class="secondary" data-edit-user="${user.id}">Изменить</button> ${
                user.id === me.id
                  ? '<span class="muted">это вы</span>'
                  : `<button type="button" class="danger" data-delete-user="${user.id}">Удалить</button>`
              }</td>
            </tr>`,
        )
        .join('')}`;
  }

  async function guard(action, successText) {
    showMessage(message, '');
    try {
      await action();
      if (successText) showMessage(message, successText, 'success');
      return true;
    } catch (error) {
      showMessage(message, describeError(error));
      return false;
    }
  }

  document.getElementById('office-form').addEventListener('submit', async (event) => {
    event.preventDefault();

    const payload = {
      name: document.getElementById('o-name').value.trim(),
      city: document.getElementById('o-city').value.trim(),
      address: document.getElementById('o-address').value.trim() || null,
      timezone: document.getElementById('o-tz').value.trim(),
      opensAt: document.getElementById('o-opens').value,
      closesAt: document.getElementById('o-closes').value,
      slotMinutes: Number(document.getElementById('o-slot').value),
      minBookingMinutes: Number(document.getElementById('o-min').value),
      maxBookingMinutes: Number(document.getElementById('o-max').value),
      bookingHorizonDays: Number(document.getElementById('o-horizon').value),
      workdays: [...document.querySelectorAll('#o-workdays input:checked')].map((input) => Number(input.value)),
    };

    if (await guard(() => api.admin.createOffice(payload), 'Офис создан')) {
      event.target.reset();
      await reloadOffices();
      await reloadRooms();
    }
  });

  document.getElementById('room-form').addEventListener('submit', async (event) => {
    event.preventDefault();

    const payload = {
      officeId: document.getElementById('r-office').value,
      name: document.getElementById('r-name').value.trim(),
      capacity: Number(document.getElementById('r-capacity').value),
      floor: document.getElementById('r-floor').value.trim() || null,
      description: document.getElementById('r-description').value.trim() || null,
    };

    if (await guard(() => api.admin.createRoom(payload), 'Комната создана')) {
      event.target.reset();
      await reloadRooms();
    }
  });

  document.getElementById('equipment-form').addEventListener('submit', async (event) => {
    event.preventDefault();

    const payload = {
      officeId: document.getElementById('e-office').value,
      name: document.getElementById('e-name').value.trim(),
      type: document.getElementById('e-type').value,
      inventoryNumber: document.getElementById('e-inventory').value.trim() || null,
      homeRoomId: document.getElementById('e-room').value || null,
      isMovable: document.getElementById('e-movable').value === 'true',
    };

    if (await guard(() => api.admin.createEquipment(payload), 'Оборудование создано')) {
      event.target.reset();
      renderEquipmentRooms();
      await reloadEquipment();
    }
  });

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('button');
    if (!button || button.disabled) return;
    const { dataset } = button;

    if (dataset.editOffice) { await editor.open('office', offices.find((record) => record.id === dataset.editOffice)); return; }
    if (dataset.editRoom) { await editor.open('room', roomCatalog.find((record) => record.id === dataset.editRoom)); return; }
    if (dataset.editEquipment) { await editor.open('equipment', equipmentCatalog.find((record) => record.id === dataset.editEquipment)); return; }
    if (dataset.editUser) { await editor.open('user', userCatalog.find((record) => record.id === dataset.editUser)); return; }

    if (dataset.toggleOffice) {
      const isActive = dataset.active !== 'true';
      if (await guard(() => api.admin.updateOffice(dataset.toggleOffice, { isActive }))) await reloadOffices();
    } else if (dataset.deleteOffice) {
      if (!window.confirm('Удалить офис вместе с его комнатами, оборудованием и бронями?')) return;
      if (await guard(() => api.admin.deleteOffice(dataset.deleteOffice), 'Офис удалён')) {
        await reloadOffices();
        await reloadRooms();
      }
    } else if (dataset.toggleRoom) {
      const isActive = dataset.active !== 'true';
      if (await guard(() => api.admin.updateRoom(dataset.toggleRoom, { isActive }))) await reloadRooms();
    } else if (dataset.deleteRoom) {
      if (!window.confirm('Удалить комнату вместе с её бронями?')) return;
      if (await guard(() => api.admin.deleteRoom(dataset.deleteRoom), 'Комната удалена')) await reloadRooms();
    } else if (dataset.toggleEquipment) {
      const isActive = dataset.active !== 'true';
      if (await guard(() => api.admin.updateEquipment(dataset.toggleEquipment, { isActive }))) {
        await reloadEquipment();
      }
    } else if (dataset.deleteEquipment) {
      if (!window.confirm('Удалить единицу оборудования?')) return;
      if (await guard(() => api.admin.deleteEquipment(dataset.deleteEquipment), 'Удалено')) {
        await reloadEquipment();
      }
    } else if (dataset.deleteUser) {
      if (!window.confirm('Удалить пользователя и организованные им брони?')) return;
      if (await guard(() => api.admin.deleteUser(dataset.deleteUser), 'Пользователь удалён')) await reloadUsers();
    }
  });

  document.addEventListener('change', async (event) => {
    const { dataset, value } = event.target;

    if (dataset.role) {
      if (await guard(() => api.admin.updateUser(dataset.role, { role: value }), 'Роль обновлена')) {
        await reloadUsers();
      }
    } else if (dataset.status) {
      if (await guard(() => api.admin.updateUser(dataset.status, { status: value }), 'Статус обновлён')) {
        await reloadUsers();
      }
    }
  });

  document.getElementById('e-office').addEventListener('change', renderEquipmentRooms);
  document.getElementById('rooms-filter').addEventListener('change', () => guard(reloadRooms));
  document.getElementById('equipment-filter').addEventListener('change', () => guard(reloadEquipment));
  function resetUserPage() { usersOffset = 0; guard(reloadUsers); }
  document.getElementById('u-status').addEventListener('change', resetUserPage);
  document.getElementById('u-role').addEventListener('change', resetUserPage);
  document.getElementById('u-limit').addEventListener('change', resetUserPage);
  document.getElementById('u-search').addEventListener('input', () => {
    clearTimeout(searchTimer);
    ++usersVersion;
    searchTimer = setTimeout(resetUserPage, 250);
  });
  document.getElementById('users-prev').addEventListener('click', () => {
    usersOffset = Math.max(0, usersOffset - Number(document.getElementById('u-limit').value));
    guard(reloadUsers);
  });
  document.getElementById('users-next').addEventListener('click', () => {
    const limit = Number(document.getElementById('u-limit').value);
    if (usersOffset + limit >= usersTotal) return;
    usersOffset += limit;
    guard(reloadUsers);
  });

  await guard(async () => {
    await reloadOffices();
    await reloadRooms();
    await reloadEquipment();
    await reloadUsers();
  });
}
    

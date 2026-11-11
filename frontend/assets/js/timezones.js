import { api } from './api.js';

let catalogPromise;
const CITY_NAMES = {
  'Europe/Kaliningrad': 'Калининград', 'Europe/Moscow': 'Москва Санкт-Петербург',
  'Europe/Samara': 'Самара', 'Europe/Volgograd': 'Волгоград', 'Europe/Saratov': 'Саратов',
  'Europe/Astrakhan': 'Астрахань', 'Europe/Ulyanovsk': 'Ульяновск', 'Asia/Yekaterinburg': 'Екатеринбург Пермь Уфа',
  'Asia/Omsk': 'Омск', 'Asia/Novosibirsk': 'Новосибирск', 'Asia/Krasnoyarsk': 'Красноярск',
  'Asia/Irkutsk': 'Иркутск', 'Asia/Yakutsk': 'Якутск', 'Asia/Vladivostok': 'Владивосток',
  'Asia/Magadan': 'Магадан', 'Asia/Kamchatka': 'Камчатка', 'Asia/Anadyr': 'Анадырь',
  'Europe/London': 'Лондон', 'Europe/Berlin': 'Берлин', 'Europe/Paris': 'Париж',
  'Europe/Minsk': 'Минск', 'Europe/Kyiv': 'Киев', 'Europe/Istanbul': 'Стамбул',
  'Asia/Almaty': 'Алматы Алма-Ата', 'Asia/Qostanay': 'Костанай Астана',
  'Asia/Tbilisi': 'Тбилиси', 'Asia/Yerevan': 'Ереван', 'Asia/Dubai': 'Дубай',
  'Asia/Tashkent': 'Ташкент', 'Asia/Bishkek': 'Бишкек', 'Asia/Tokyo': 'Токио',
  'Asia/Shanghai': 'Шанхай Пекин', 'Asia/Bangkok': 'Бангкок Пхукет',
  'America/New_York': 'Нью-Йорк', 'America/Los_Angeles': 'Лос-Анджелес',
  'America/Chicago': 'Чикаго', 'Australia/Sydney': 'Сидней', UTC: 'Всемирное время',
};
const TRANSLITERATION = { а:'a', б:'b', в:'v', г:'g', д:'d', е:'e', ё:'e', ж:'zh', з:'z', и:'i', й:'y', к:'k', л:'l', м:'m', н:'n', о:'o', п:'p', р:'r', с:'s', т:'t', у:'u', ф:'f', х:'kh', ц:'ts', ч:'ch', ш:'sh', щ:'sch', ъ:'', ы:'y', ь:'', э:'e', ю:'yu', я:'ya' };
const normalize = (value) => value.toLowerCase().replace(/[а-яё]/g, (character) => TRANSLITERATION[character]).replaceAll('_', ' ').replaceAll('−', '-').trim();

export function timezoneCatalog() {
  if (!catalogPromise) catalogPromise = api.offices.timezones().then(({ timezones }) => timezones).catch((error) => { catalogPromise = null; throw error; });
  return catalogPromise;
}

export async function attachTimezonePicker(input) {
  const zones = await timezoneCatalog();
  const known = new Set(zones.map((zone) => zone.id));
  const entries = zones.map((zone) => ({ ...zone, label: CITY_NAMES[zone.id] || '', search: normalize(`${zone.id} ${CITY_NAMES[zone.id] || ''} ${zone.utcOffset} ${zone.utcOffset.replace(/([+-])0/, '$1').replace(':00', '')}`) }));
  input.autocomplete = 'off';
  input.spellcheck = false;
  input.setAttribute('role', 'combobox');
  input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-expanded', 'false');
  const list = document.createElement('div');
  list.id = `${input.id}-options`;
  list.className = 'timezone-options';
  list.setAttribute('role', 'listbox');
  list.hidden = true;
  input.parentElement.classList.add('timezone-field');
  input.insertAdjacentElement('afterend', list);
  input.setAttribute('aria-controls', list.id);
  let activeIndex = -1;
  let matches = [];

  function validate() {
    input.setCustomValidity(known.has(input.value.trim()) ? '' : 'Выберите часовой пояс из подсказок.');
  }
  function close() {
    list.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    activeIndex = -1;
  }
  function select(index) {
    if (!matches[index]) return;
    input.value = matches[index].id;
    validate();
    close();
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  function highlight() {
    [...list.children].forEach((option, index) => option.setAttribute('aria-selected', String(index === activeIndex)));
    if (activeIndex >= 0) {
      input.setAttribute('aria-activedescendant', list.children[activeIndex].id);
      list.children[activeIndex].scrollIntoView({ block: 'nearest' });
    }
  }
  function render() {
    const query = normalize(input.value);
    matches = entries.filter((zone) => !query || zone.search.includes(query)).sort((a, b) => Number(b.id === input.value) - Number(a.id === input.value) || a.id.localeCompare(b.id)).slice(0, 60);
    list.replaceChildren();
    activeIndex = -1;
    input.removeAttribute('aria-activedescendant');
    for (const [index, zone] of matches.entries()) {
      const option = document.createElement('div');
      option.id = `${list.id}-${index}`;
      option.className = 'timezone-option';
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', 'false');
      const name = document.createElement('strong');
      name.textContent = zone.label ? `${zone.label} · ${zone.id}` : zone.id;
      const offset = document.createElement('small');
      offset.textContent = zone.utcOffset;
      option.append(name, offset);
      option.addEventListener('mousedown', (event) => event.preventDefault());
      option.addEventListener('click', () => select(index));
      list.append(option);
    }
    if (!matches.length) {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = 'Совпадений нет. Попробуйте название города латиницей или UTC+03.';
      list.append(empty);
    }
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }
  input.addEventListener('input', () => { validate(); render(); });
  input.addEventListener('focus', render);
  input.addEventListener('blur', () => setTimeout(close, 120));
  input.addEventListener('change', validate);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') { if (!list.hidden) { event.preventDefault(); event.stopPropagation(); close(); } return; }
    if (event.key === 'Tab') { close(); return; }
    if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault();
      if (list.hidden) render();
      if (!matches.length) return;
      activeIndex = activeIndex < 0 ? (event.key === 'ArrowDown' ? 0 : matches.length - 1) : (activeIndex + (event.key === 'ArrowDown' ? 1 : -1) + matches.length) % matches.length;
      highlight();
    } else if (event.key === 'Enter' && !list.hidden) {
      event.preventDefault();
      if (activeIndex >= 0) select(activeIndex);
      else if (matches.length === 1) select(0);
      else close();
    }
  });
  input.form?.addEventListener('reset', () => queueMicrotask(() => { close(); validate(); }));
  validate();
  return { refresh: () => { close(); validate(); }, close };
}

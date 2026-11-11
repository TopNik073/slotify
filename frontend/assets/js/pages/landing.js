import { session } from '../api.js';

if (session.isAuthenticated) {
  document.querySelectorAll('[data-start]').forEach((link) => { link.href = '/rooms.html'; link.textContent = 'К бронированию ↗'; });
  document.querySelectorAll('[data-login]').forEach((link) => { link.hidden = true; });
}

document.querySelectorAll('[data-demo-room]').forEach((button) => button.addEventListener('click', () => {
  document.querySelectorAll('[data-demo-room]').forEach((slot) => {
    slot.classList.toggle('chosen', slot === button);
    slot.setAttribute('aria-pressed', String(slot === button));
  });
  const [hour, minute] = button.dataset.demoTime.split(':').map(Number);
  const end = hour * 60 + minute + 30;
  const endTime = `${String(Math.floor(end / 60)).padStart(2, '0')}:${String(end % 60).padStart(2, '0')}`;
  document.getElementById('demo-selection').textContent = `${button.dataset.demoRoom} · ${button.dataset.demoTime}–${endTime}`;
}));

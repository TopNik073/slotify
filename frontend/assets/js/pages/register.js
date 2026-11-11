import { api, session } from '/assets/js/api.js';
import { describeError, showMessage } from '/assets/js/ui.js';

const message = document.getElementById('message');
const detailsForm = document.getElementById('details-form');
const codeForm = document.getElementById('code-form');

document.getElementById('google').addEventListener('click', async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  showMessage(message, '');
  try {
    const { authorizationUrl } = await api.auth.googleLoginUrl(
      document.getElementById('email').value.trim() || undefined,
      '/rooms.html',
    );
    window.location.href = authorizationUrl;
  } catch (error) {
    showMessage(message, describeError(error));
    button.disabled = false;
  }
});

// Invitation emails link here with the address prefilled, so the person claims the
// placeholder account that was created when they were added to a booking.
const invitedEmail = new URLSearchParams(window.location.search).get('email');
if (invitedEmail) document.getElementById('email').value = invitedEmail;

let pending = null;

detailsForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = document.getElementById('submit-details');
  button.disabled = true;
  showMessage(message, '');

  const payload = {
    email: document.getElementById('email').value.trim(),
    password: document.getElementById('password').value,
    fullName: document.getElementById('fullName').value.trim() || null,
  };

  try {
    await api.auth.register(payload);
    pending = { email: payload.email, password: payload.password };

    detailsForm.hidden = true;
    codeForm.hidden = false;
    document.getElementById('code-hint').textContent = `Код отправлен на ${payload.email}`;
    document.getElementById('code').focus();
  } catch (error) {
    showMessage(message, describeError(error));
  } finally {
    button.disabled = false;
  }
});

codeForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = document.getElementById('submit-code');
  button.disabled = true;
  showMessage(message, '');

  try {
    const tokens = await api.auth.confirm('register', {
      ...pending,
      code: document.getElementById('code').value.trim(),
    });
    session.save(tokens.accessToken, tokens.refreshToken);
    window.location.replace('/rooms.html');
  } catch (error) {
    showMessage(message, describeError(error));
  } finally {
    button.disabled = false;
  }
});
    

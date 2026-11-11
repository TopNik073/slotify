import { api, session } from '/assets/js/api.js';
import { describeError, showMessage } from '/assets/js/ui.js';

const message = document.getElementById('message');
const credentialsForm = document.getElementById('credentials-form');
const codeForm = document.getElementById('code-form');
const requestedNext = new URL(new URLSearchParams(window.location.search).get('next') || '/rooms.html', window.location.origin);
const nextUrl = requestedNext.origin === window.location.origin ? requestedNext.pathname + requestedNext.search : '/rooms.html';

if (session.isAuthenticated) window.location.replace(nextUrl);
if (new URLSearchParams(window.location.search).get('session') === 'expired') {
  showMessage(message, 'Сессия истекла. Войдите снова, чтобы продолжить.', 'info');
}

let pending = null;

credentialsForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = document.getElementById('submit-credentials');
  button.disabled = true;
  showMessage(message, '');

  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;

  try {
    await api.auth.login(email, password);
    pending = { email, password };

    credentialsForm.hidden = true;
    codeForm.hidden = false;
    document.getElementById('code-hint').textContent = `Код отправлен на ${email}`;
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
    const tokens = await api.auth.confirm('login', {
      ...pending,
      code: document.getElementById('code').value.trim(),
    });
    session.save(tokens.accessToken, tokens.refreshToken);
    window.location.replace(nextUrl);
  } catch (error) {
    showMessage(message, describeError(error));
  } finally {
    button.disabled = false;
  }
});

document.getElementById('back').addEventListener('click', () => {
  codeForm.hidden = true;
  credentialsForm.hidden = false;
  showMessage(message, '');
});

document.getElementById('google').addEventListener('click', async (event) => {
  event.target.disabled = true;
  try {
    const { authorizationUrl } = await api.auth.googleLoginUrl(
      document.getElementById('email').value.trim() || undefined,
          nextUrl,
    );
    window.location.href = authorizationUrl;
  } catch (error) {
    showMessage(message, describeError(error));
    event.target.disabled = false;
  }
});
    

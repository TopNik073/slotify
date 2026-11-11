from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken as InvalidFernetToken

from src.core.config import config
from src.exceptions import ServerError


class TokenCipher:
    """
    Symmetric encryption for third-party credentials kept in the database.

    Google refresh tokens are long-lived and grant calendar access, so they never touch the
    database in plaintext. Rotating ``TOKEN_ENCRYPTION_KEY`` invalidates every stored token and
    forces users to reconnect their calendar.
    """

    def __init__(self) -> None:
        self._fernet = Fernet(config.TOKEN_ENCRYPTION_KEY.get_secret_value().encode())

    def encrypt(self, value: str | None) -> str | None:
        if value is None:
            return None

        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str | None) -> str | None:
        if value is None:
            return None

        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidFernetToken as exc:
            msg = 'Stored token cannot be decrypted, TOKEN_ENCRYPTION_KEY may have changed'
            raise ServerError(message=msg, code='token_decryption_failed') from exc

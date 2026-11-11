from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Literal
from uuid import UUID

from jose import JWTError
from jose import jwt

from src.core.config import config
from src.exceptions import InvalidToken

TokenType = Literal['access', 'refresh']


class JWTHandler:
    """Issues and inspects the application's own access/refresh tokens."""

    def __init__(self) -> None:
        self._secret = config.JWT_SECRET.get_secret_value()
        self._algorithm = config.JWT_ALGORITHM

    def _create_token(
        self,
        user_id: UUID,
        token_type: TokenType,
        lifetime_seconds: int,
    ) -> tuple[str, datetime]:
        issued_at = datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=lifetime_seconds)

        payload = {
            'sub': str(user_id),
            'type': token_type,
            'iat': int(issued_at.timestamp()),
            'exp': int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)

        return token, expires_at

    def get_access_token(self, user_id: UUID) -> tuple[str, datetime]:
        return self._create_token(user_id, 'access', config.ACCESS_TOKEN_EXP)

    def get_refresh_token(self, user_id: UUID) -> tuple[str, datetime]:
        return self._create_token(user_id, 'refresh', config.REFRESH_TOKEN_EXP)

    def decode_token(self, token: str) -> dict[str, Any]:
        """
        Verify the signature but not the expiry.

        Expiry is reported separately through ``is_token_expired`` so that callers can tell an
        expired token from a forged one instead of getting the same error for both.
        """
        try:
            return jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={'verify_exp': False},
            )
        except JWTError as exc:
            raise InvalidToken from exc

    def get_token_expiration(self, token: str) -> datetime:
        payload = self.decode_token(token)
        expires_at = payload.get('exp')
        if expires_at is None:
            raise InvalidToken

        return datetime.fromtimestamp(expires_at, tz=UTC)

    def is_token_expired(self, token: str) -> bool:
        return datetime.now(UTC) >= self.get_token_expiration(token)

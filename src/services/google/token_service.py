from typing import Annotated
from uuid import UUID

from fastapi import Depends

from src.core.config import config
from src.core.logger import get_logger
from src.database.repository import GoogleAccount
from src.database.repository import GoogleAccountRepository
from src.exceptions import GoogleCalendarNotConnected
from src.integrations.google import GoogleAuthClient
from src.integrations.google import GoogleTokenResponse
from src.integrations.google import GoogleUserInfo
from src.services.security import TokenCipher

logger = get_logger(__name__)


class GoogleTokenService:
    """
    Owns the stored Google credentials of a user.

    Tokens are encrypted on the way in and decrypted on the way out, so the rest of the
    application only ever handles usable plaintext tokens and never persists them.
    """

    def __init__(
        self,
        accounts_repository: Annotated[GoogleAccountRepository, Depends(GoogleAccountRepository)],
        auth_client: Annotated[GoogleAuthClient, Depends(GoogleAuthClient)],
    ):
        self._accounts = accounts_repository
        self._auth = auth_client
        self._cipher = TokenCipher()

    async def link_account(
        self,
        user_id: UUID,
        user_info: GoogleUserInfo,
        tokens: GoogleTokenResponse,
    ) -> GoogleAccount:
        """
        Store or refresh the link between a Slotify user and their Google account.

        A refresh token is only kept when Google actually sent one: on repeat consent it omits
        the field, and overwriting the stored value with None would silently revoke our access.
        """
        existing = await self._accounts.get_by_user_id(user_id)
        granted_scopes = tokens.scopes
        calendar_connected = any(scope in granted_scopes for scope in config.google_credentials.calendar_scopes)

        if existing is None:
            account = GoogleAccount(
                user_id=user_id,
                google_sub=user_info.sub,
                email=user_info.email,
                access_token=self._cipher.encrypt(tokens.access_token),
                refresh_token=self._cipher.encrypt(tokens.refresh_token),
                token_expires_at=tokens.expires_at,
                scopes=granted_scopes,
                calendar_connected=calendar_connected,
            )
            return await self._accounts.create(account)

        existing.google_sub = user_info.sub
        existing.email = user_info.email
        existing.access_token = self._cipher.encrypt(tokens.access_token)
        existing.token_expires_at = tokens.expires_at
        existing.scopes = granted_scopes or existing.scopes
        existing.calendar_connected = calendar_connected or existing.calendar_connected

        if tokens.refresh_token:
            existing.refresh_token = self._cipher.encrypt(tokens.refresh_token)

        return await self._accounts.update(existing)

    async def get_account(self, user_id: UUID) -> GoogleAccount | None:
        return await self._accounts.get_by_user_id(user_id)

    async def get_access_token(self, user_id: UUID) -> str:
        """
        A usable access token for this user, refreshing it when it is about to expire.

        Raises ``GoogleCalendarNotConnected`` when the user never granted calendar access, which
        callers treat as "skip the calendar" rather than as an error.
        """
        account = await self._accounts.get_by_user_id(user_id)
        if account is None or not account.calendar_connected:
            raise GoogleCalendarNotConnected

        if not account.is_access_token_expired:
            token = self._cipher.decrypt(account.access_token)
            if token:
                return token

        refresh_token = self._cipher.decrypt(account.refresh_token)
        if not refresh_token:
            await logger.awarning('Google account has no refresh token, reconnect required', user_id=str(user_id))
            raise GoogleCalendarNotConnected(message='Google access expired, reconnect your calendar')

        tokens = await self._auth.refresh_access_token(refresh_token)

        account.access_token = self._cipher.encrypt(tokens.access_token)
        account.token_expires_at = tokens.expires_at
        if tokens.refresh_token:
            account.refresh_token = self._cipher.encrypt(tokens.refresh_token)

        await self._accounts.update(account)

        return tokens.access_token

    async def disconnect(self, user_id: UUID) -> None:
        account = await self._accounts.get_by_user_id(user_id)
        if account is None:
            return

        refresh_token = self._cipher.decrypt(account.refresh_token)
        if refresh_token:
            await self._auth.revoke(refresh_token)

        await self._accounts.delete(account.identifier)

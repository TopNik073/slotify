from urllib.parse import urlencode

from pydantic import ValidationError

from src.core.config import config
from src.core.logger import get_logger
from src.exceptions import GoogleAuthFailed
from src.integrations.google.entities import GoogleTokenResponse
from src.integrations.google.entities import GoogleUserInfo
from src.integrations.http_client import BaseHTTPClient
from src.integrations.http_client import HTTPClientError

logger = get_logger(__name__)


class GoogleAuthClient(BaseHTTPClient):
    """OAuth2 authorization code flow against Google's endpoints."""

    def __init__(self) -> None:
        super().__init__(timeout=10.0)
        self._credentials = config.google_credentials

    def build_authorization_url(
        self,
        state: str,
        *,
        scopes: list[str] | None = None,
        login_hint: str | None = None,
    ) -> str:
        """
        The URL the browser is sent to for consent.

        ``access_type=offline`` with ``prompt=consent`` is what makes Google return a refresh
        token; without it we could create one calendar event and then lose access for good.
        ``include_granted_scopes`` keeps previously granted scopes when asking for the calendar
        on top of a plain sign-in.
        """
        params = {
            'client_id': self._credentials.client_id,
            'redirect_uri': self._credentials.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(scopes or self._credentials.scopes),
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent',
            'include_granted_scopes': 'true',
        }
        if login_hint:
            params['login_hint'] = login_hint

        return f'{self._credentials.auth_uri}?{urlencode(params)}'

    async def exchange_code(self, code: str) -> GoogleTokenResponse:
        payload = await self._token_request(
            {
                'code': code,
                'client_id': self._credentials.client_id,
                'client_secret': self._credentials.client_secret.get_secret_value(),
                'redirect_uri': self._credentials.redirect_uri,
                'grant_type': 'authorization_code',
            }
        )

        return self._parse_token(payload)

    async def refresh_access_token(self, refresh_token: str) -> GoogleTokenResponse:
        payload = await self._token_request(
            {
                'refresh_token': refresh_token,
                'client_id': self._credentials.client_id,
                'client_secret': self._credentials.client_secret.get_secret_value(),
                'grant_type': 'refresh_token',
            }
        )

        return self._parse_token(payload)

    async def fetch_user_info(self, access_token: str) -> GoogleUserInfo:
        try:
            payload = await self.request(
                'GET',
                self._credentials.userinfo_uri,
                headers={'Authorization': f'Bearer {access_token}'},
            )
        except HTTPClientError as exc:
            raise GoogleAuthFailed(message='Could not read the Google profile') from exc

        try:
            return GoogleUserInfo.model_validate(payload)
        except ValidationError as exc:
            await logger.aerror('Unexpected Google userinfo payload', payload=payload)
            raise GoogleAuthFailed(message='Unexpected Google profile response') from exc

    async def revoke(self, token: str) -> None:
        """Best effort: a token that cannot be revoked remotely is still dropped locally."""
        try:
            await self.request(
                'POST',
                self._credentials.revoke_uri,
                data={'token': token},
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
            )
        except HTTPClientError:
            await logger.awarning('Could not revoke a Google token, dropping it locally')

    async def _token_request(self, data: dict[str, str]) -> dict:
        try:
            return await self.request(
                'POST',
                self._credentials.token_uri,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
            )
        except HTTPClientError as exc:
            raise GoogleAuthFailed(message='Google rejected the authorization request') from exc

    @staticmethod
    def _parse_token(payload: dict) -> GoogleTokenResponse:
        try:
            return GoogleTokenResponse.model_validate(payload)
        except ValidationError as exc:
            raise GoogleAuthFailed(message='Unexpected Google token response') from exc

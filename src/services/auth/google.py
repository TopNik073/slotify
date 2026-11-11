import secrets

from datetime import UTC
from datetime import datetime
from typing import Annotated
from urllib.parse import urlencode
from urllib.parse import urlsplit

from fastapi import Depends

from src.core.config import config
from src.core.logger import get_logger
from src.database.enums import UserStatus
from src.database.repository import BookingParticipantRepository
from src.database.repository import User
from src.database.repository import UserRepository
from src.exceptions import AccountDisabled
from src.exceptions import GoogleStateMismatch
from src.integrations.google import GoogleAuthClient
from src.integrations.google import GoogleUserInfo
from src.integrations.redis import RedisClient
from src.services.auth.models import JWTToken
from src.services.auth.models import JWTTokens
from src.services.google import GoogleTokenService
from src.services.security import JWTHandler

logger = get_logger(__name__)

_STATE_PREFIX = 'auth:google:state'
_STATE_TTL = 600
_RETURN_PATHS = {'/', '/rooms.html', '/my-bookings.html', '/admin.html'}


def safe_return_path(value: str | None) -> str:
    if not value or value.startswith('//') or '\\' in value or any(ord(character) < 32 for character in value):  # noqa: PLR2004
        return '/rooms.html'
    try:
        parsed = urlsplit(value)
    except ValueError:
        return '/rooms.html'
    if parsed.scheme or parsed.netloc or parsed.path not in _RETURN_PATHS or not value.startswith('/'):
        return '/rooms.html'
    return value


class GoogleAuthService:
    """
    Sign-in with Google, which doubles as granting calendar access.

    One round trip asks for both the profile and the calendar scope, so a user who signed in
    with Google can immediately have their bookings pushed to their own calendar without a
    second consent screen.
    """

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        users_repository: Annotated[UserRepository, Depends(UserRepository)],
        participant_repository: Annotated[BookingParticipantRepository, Depends(BookingParticipantRepository)],
        auth_client: Annotated[GoogleAuthClient, Depends(GoogleAuthClient)],
        token_service: Annotated[GoogleTokenService, Depends(GoogleTokenService)],
        redis_cache: Annotated[RedisClient, Depends(RedisClient)],
        jwt_handler: Annotated[JWTHandler, Depends(JWTHandler)],
    ):
        self._users = users_repository
        self._participants = participant_repository
        self._auth = auth_client
        self._tokens = token_service
        self._cache = redis_cache
        self._jwt = jwt_handler

    async def start(self, *, login_hint: str | None = None, next_path: str | None = None) -> str:
        """
        Begin the flow and return the URL to send the browser to.

        The ``state`` value is kept in Redis and checked on the way back, which is what stops a
        third party from feeding us an authorization code of their own.
        """
        state = secrets.token_urlsafe(32)
        await self._cache.set(
            f'{_STATE_PREFIX}:{state}',
            {
                'created_at': datetime.now(UTC).isoformat(),
                'login_hint': login_hint,
                'next': safe_return_path(next_path),
            },
            expire=_STATE_TTL,
        )

        return self._auth.build_authorization_url(state, login_hint=login_hint)

    async def return_path(self, state: str | None) -> str:
        data = await self._cache.get(f'{_STATE_PREFIX}:{state}') if state else None
        return safe_return_path(data.get('next') if data else None)

    async def complete(self, code: str, state: str) -> JWTTokens:
        """Exchange the code, resolve the account behind it and issue our own tokens."""
        key = f'{_STATE_PREFIX}:{state}'
        if not await self._cache.exists(key):
            raise GoogleStateMismatch

        await self._cache.delete(key)

        tokens = await self._auth.exchange_code(code)
        user_info = await self._auth.fetch_user_info(tokens.access_token)

        user = await self._resolve_user(user_info)
        if user.status is UserStatus.disabled:
            raise AccountDisabled

        await self._tokens.link_account(user.identifier, user_info, tokens)

        return self._issue_tokens(user)

    async def _resolve_user(self, user_info: GoogleUserInfo) -> User:
        """
        Find the Slotify account for a Google identity, creating one if needed.

        Matching by ``google_sub`` first and by email second is what links a Google sign-in to an
        account that already exists, including an ``invited`` placeholder created when somebody
        added this address to a booking. Adopting the placeholder rather than failing on the
        unique email is the whole reason invitations can precede registration.
        """
        existing = await self._users.get_by_google_sub(user_info.sub)
        if existing is not None:
            if existing.status is UserStatus.disabled:
                return existing
            avatar = user_info.picture or existing.avatar_url
            name = existing.full_name or user_info.name
            if avatar != existing.avatar_url or name != existing.full_name:
                existing.avatar_url = avatar
                existing.full_name = name
                return await self._users.update(existing)
            return existing

        by_email = await self._users.get_by_email(user_info.email)
        if by_email is not None:
            by_email.google_sub = user_info.sub
            by_email.full_name = by_email.full_name or user_info.name
            by_email.avatar_url = user_info.picture or by_email.avatar_url

            if by_email.status is UserStatus.invited:
                by_email.status = UserStatus.active
                await logger.ainfo('Invited placeholder activated via Google', email=by_email.email)

            return await self._users.update(by_email)

        created = await self._users.create(
            User(
                email=user_info.email,
                full_name=user_info.name,
                avatar_url=user_info.picture,
                google_sub=user_info.sub,
                status=UserStatus.active,
            )
        )

        # Invitations may have been addressed to this email before the account existed.
        await self._participants.link_user_by_email(created.email, created.identifier)

        return created

    def _issue_tokens(self, user: User) -> JWTTokens:
        """
        No email code here, unlike password login.

        Google already verified the address, so a second factor over the same mailbox would add
        friction without adding assurance.
        """
        access_token, access_exp = self._jwt.get_access_token(user_id=user.identifier)
        refresh_token, refresh_exp = self._jwt.get_refresh_token(user_id=user.identifier)

        return JWTTokens(
            access=JWTToken(token=access_token, expires_at=access_exp),
            refresh=JWTToken(token=refresh_token, expires_at=refresh_exp),
        )

    async def disconnect(self, user: User) -> None:
        await self._tokens.disconnect(user.identifier)

    @staticmethod
    def callback_redirect_url(
        tokens: JWTTokens | None = None,
        *,
        error: str | None = None,
        next_path: str | None = None,
    ) -> str:
        """
        Where the browser lands after Google redirects back.

        Tokens travel in the URL fragment: a fragment is never sent to the server, so they stay
        out of access logs and out of the ``Referer`` header of the next request.
        """
        base = f'{config.PUBLIC_BASE_URL.rstrip("/")}/auth-callback.html'

        params = {'next': safe_return_path(next_path)}
        if error is not None or tokens is None:
            params['error'] = error or 'unknown_error'
        else:
            params.update(accessToken=tokens.access.token, refreshToken=tokens.refresh.token)
        return f'{base}#{urlencode(params)}'

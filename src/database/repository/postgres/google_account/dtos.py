from datetime import UTC
from datetime import datetime
from datetime import timedelta
from uuid import UUID

from pydantic import Field

from src.database.repository.base import BaseModelIdentifiable
from src.database.repository.base import PydanticToORMModelMixin
from src.database.repository.base import TimestampedModelMixin

# Refresh a little early so a token cannot expire midway through a Calendar call.
_EXPIRY_SKEW = timedelta(seconds=60)


class GoogleAccount(BaseModelIdentifiable, PydanticToORMModelMixin, TimestampedModelMixin):
    """Tokens here are ciphertext; use ``GoogleTokenService`` to read or write them."""

    user_id: UUID
    google_sub: str
    email: str

    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None

    scopes: list[str] = Field(default_factory=list)
    calendar_connected: bool = False

    @property
    def is_access_token_expired(self) -> bool:
        if self.access_token is None or self.token_expires_at is None:
            return True

        return datetime.now(UTC) >= self.token_expires_at - _EXPIRY_SKEW

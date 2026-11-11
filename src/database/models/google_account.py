from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.database.models.base import BaseORM
from src.database.models.base import TimestampMixin


class GoogleAccountORM(BaseORM, TimestampMixin):
    """
    OAuth2 state for one user's Google account.

    Both tokens are stored Fernet-encrypted (see ``src.services.security.TokenCipher``);
    nothing in this table is usable without ``TOKEN_ENCRYPTION_KEY``.
    """

    __tablename__ = 'google_accounts'

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        unique=True,
    )

    google_sub: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320))

    access_token: Mapped[str | None] = mapped_column(Text, default=None)
    refresh_token: Mapped[str | None] = mapped_column(Text, default=None)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    scopes: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list)

    # True once the user granted the calendar scope, i.e. we may create events on their behalf.
    calendar_connected: Mapped[bool] = mapped_column(Boolean, default=False)

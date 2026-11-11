from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.database.enums import UserRole
from src.database.enums import UserStatus
from src.database.models.base import BaseORM
from src.database.models.base import TimestampMixin
from src.database.models.base import enum_column


class UserORM(BaseORM, TimestampMixin):
    __tablename__ = 'users'

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), default=None)

    # Null for accounts that only ever signed in with Google, and for `invited` placeholders.
    password_hash: Mapped[str | None] = mapped_column(String(255), default=None)

    role: Mapped[UserRole] = mapped_column(enum_column(UserRole, 'user_role'), default=UserRole.user)
    status: Mapped[UserStatus] = mapped_column(enum_column(UserStatus, 'user_status'), default=UserStatus.active)

    office_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('offices.id', ondelete='SET NULL'),
        default=None,
        index=True,
    )

    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), default=None)

from uuid import UUID

from pydantic import field_validator

from src.database.enums import UserRole
from src.database.enums import UserStatus
from src.database.repository.base import BaseModelIdentifiable
from src.database.repository.base import PydanticToORMModelMixin
from src.database.repository.base import TimestampedModelMixin


class User(BaseModelIdentifiable, PydanticToORMModelMixin, TimestampedModelMixin):
    email: str
    full_name: str | None = None
    password_hash: str | None = None

    role: UserRole = UserRole.user
    status: UserStatus = UserStatus.active

    office_id: UUID | None = None

    google_sub: str | None = None
    avatar_url: str | None = None

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Addresses are matched case-insensitively, so they are stored lowercased."""
        return value.strip().lower()

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.admin

    @property
    def can_log_in(self) -> bool:
        return self.status is UserStatus.active

    @property
    def display_name(self) -> str:
        return self.full_name or self.email

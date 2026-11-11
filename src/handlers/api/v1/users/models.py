from uuid import UUID

from src.database.enums import UserRole
from src.database.enums import UserStatus
from src.handlers.api.models import APIModel


class UserResponse(APIModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: UserRole
    status: UserStatus
    office_id: UUID | None = None
    avatar_url: str | None = None


class CurrentUserResponse(UserResponse):
    google_calendar_connected: bool = False


class UserListResponse(APIModel):
    users: list[UserResponse]


class AdminUserListResponse(UserListResponse):
    total: int
    limit: int
    offset: int


class UpdateProfileRequest(APIModel):
    full_name: str | None = None
    office_id: UUID | None = None

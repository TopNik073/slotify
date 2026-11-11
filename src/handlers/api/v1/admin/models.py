from datetime import time
from uuid import UUID

from pydantic import Field

from src.core.config import config
from src.database.enums import EquipmentType
from src.database.enums import UserRole
from src.database.enums import UserStatus
from src.handlers.api.models import APIModel


class OfficeCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=512)

    timezone: str = 'UTC'
    workdays: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    opens_at: time = time(9, 0)
    closes_at: time = time(20, 0)

    slot_minutes: int = Field(default=config.DEFAULT_SLOT_MINUTES, ge=5, le=240)
    min_booking_minutes: int = Field(default=config.DEFAULT_MIN_BOOKING_MINUTES, ge=5)
    max_booking_minutes: int = Field(default=config.DEFAULT_MAX_BOOKING_MINUTES, ge=5)
    booking_horizon_days: int = Field(default=config.DEFAULT_BOOKING_HORIZON_DAYS, ge=1, le=730)

    is_active: bool = True


class OfficeUpdateRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None

    timezone: str | None = None
    workdays: list[int] | None = None
    opens_at: time | None = None
    closes_at: time | None = None

    slot_minutes: int | None = Field(default=None, ge=5, le=240)
    min_booking_minutes: int | None = Field(default=None, ge=5)
    max_booking_minutes: int | None = Field(default=None, ge=5)
    booking_horizon_days: int | None = Field(default=None, ge=1, le=730)

    is_active: bool | None = None


class RoomCreateRequest(APIModel):
    office_id: UUID
    name: str = Field(min_length=1, max_length=255)
    capacity: int = Field(default=1, ge=1, le=1000)
    floor: str | None = Field(default=None, max_length=32)
    description: str | None = None
    is_active: bool = True


class RoomUpdateRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    capacity: int | None = Field(default=None, ge=1, le=1000)
    floor: str | None = None
    description: str | None = None
    is_active: bool | None = None


class EquipmentCreateRequest(APIModel):
    office_id: UUID
    name: str = Field(min_length=1, max_length=255)
    type: EquipmentType
    inventory_number: str | None = Field(default=None, max_length=64)
    description: str | None = None
    home_room_id: UUID | None = None
    is_movable: bool = True
    is_active: bool = True


class EquipmentUpdateRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: EquipmentType | None = None
    inventory_number: str | None = None
    description: str | None = None
    home_room_id: UUID | None = None
    is_movable: bool | None = None
    is_active: bool | None = None


class UserUpdateRequest(APIModel):
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole | None = None
    status: UserStatus | None = None
    office_id: UUID | None = None

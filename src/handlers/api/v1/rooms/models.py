from datetime import date
from datetime import datetime
from uuid import UUID

from src.handlers.api.models import APIModel
from src.handlers.api.v1.offices.models import OfficeResponse


class RoomResponse(APIModel):
    id: UUID
    office_id: UUID
    name: str
    capacity: int
    floor: str | None = None
    description: str | None = None
    is_active: bool


class RoomListResponse(APIModel):
    rooms: list[RoomResponse]


class SlotResponse(APIModel):
    starts_at: datetime
    ends_at: datetime
    is_free: bool
    booking_id: UUID | None = None
    is_mine: bool = False


class RoomAvailabilityResponse(APIModel):
    room: RoomResponse
    slots: list[SlotResponse]


class AvailabilityResponse(APIModel):
    office: OfficeResponse
    day: date
    rooms: list[RoomAvailabilityResponse]

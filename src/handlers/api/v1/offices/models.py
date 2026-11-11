from datetime import time
from uuid import UUID

from src.handlers.api.models import APIModel


class OfficeResponse(APIModel):
    id: UUID
    name: str
    city: str
    address: str | None = None

    timezone: str
    workdays: list[int]
    opens_at: time
    closes_at: time

    slot_minutes: int
    min_booking_minutes: int
    max_booking_minutes: int
    booking_horizon_days: int

    is_active: bool


class OfficeListResponse(APIModel):
    offices: list[OfficeResponse]


class TimezoneResponse(APIModel):
    id: str
    utc_offset: str


class TimezoneListResponse(APIModel):
    timezones: list[TimezoneResponse]

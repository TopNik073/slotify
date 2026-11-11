from datetime import date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field

from src.database.enums import RecurrenceFrequency
from src.database.repository import Booking
from src.database.repository import BookingParticipant
from src.database.repository import Equipment
from src.database.repository import Office
from src.database.repository import Room


class RecurrenceDraft(BaseModel):
    frequency: RecurrenceFrequency
    interval: int = Field(default=1, ge=1, le=12)
    byweekday: list[int] | None = None
    until: datetime | None = None
    count: int | None = Field(default=None, ge=2)


class BookingDraft(BaseModel):
    """What the organizer asked for, before any of it is validated against the office policy."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None

    starts_at: datetime
    ends_at: datetime

    room_id: UUID | None = None
    equipment_ids: list[UUID] = Field(default_factory=list)

    participant_user_ids: list[UUID] = Field(default_factory=list)
    participant_emails: list[EmailStr] = Field(default_factory=list)

    recurrence: RecurrenceDraft | None = None


class BookingDetails(BaseModel):
    """A booking with everything needed to render it, resolved in one go."""

    booking: Booking
    room: Room | None = None
    equipment: list[Equipment] = Field(default_factory=list)
    participants: list[BookingParticipant] = Field(default_factory=list)

    # False when the booking was saved but Google Calendar could not be updated.
    calendar_synced: bool = False


class SeriesDetails(BaseModel):
    occurrences: list[BookingDetails]
    series_id: UUID | None = None


class SlotAvailability(BaseModel):
    starts_at: datetime
    ends_at: datetime
    is_free: bool
    booking_id: UUID | None = None
    is_mine: bool = False


class RoomAvailability(BaseModel):
    room: Room
    slots: list[SlotAvailability]


class OfficeDayAvailability(BaseModel):
    office: Office
    day: date
    rooms: list[RoomAvailability]

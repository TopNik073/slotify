from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime
from pydantic import EmailStr
from pydantic import Field

from src.database.enums import BookingStatus
from src.database.enums import ParticipantResponse
from src.database.enums import RecurrenceFrequency
from src.handlers.api.models import APIModel
from src.handlers.api.v1.equipment.models import EquipmentResponse
from src.handlers.api.v1.rooms.models import RoomResponse
from src.services.booking import BookingDetails


class RecurrenceRequest(APIModel):
    frequency: RecurrenceFrequency
    interval: int = Field(default=1, ge=1, le=12)

    # ISO weekdays for a weekly series, 1 = Monday .. 7 = Sunday.
    byweekday: list[int] | None = None

    until: AwareDatetime | None = None
    count: int | None = Field(default=None, ge=2)


class CreateBookingRequest(APIModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None

    # Aware on purpose: a naive timestamp would be silently read as UTC and shift the booking
    # for every office that is not on UTC, so it is rejected at the boundary with a 422.
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    room_id: UUID | None = None
    equipment_ids: list[UUID] = Field(default_factory=list)

    participant_user_ids: list[UUID] = Field(default_factory=list)
    participant_emails: list[EmailStr] = Field(default_factory=list)

    recurrence: RecurrenceRequest | None = None


class RescheduleBookingRequest(APIModel):
    starts_at: AwareDatetime
    ends_at: AwareDatetime


class RespondToBookingRequest(APIModel):
    response: ParticipantResponse


class ParticipantResponseModel(APIModel):
    email: str
    user_id: UUID | None = None
    is_organizer: bool
    response: ParticipantResponse


class BookingResponse(APIModel):
    id: UUID
    title: str
    description: str | None = None

    organizer_id: UUID
    office_id: UUID
    series_id: UUID | None = None

    starts_at: datetime
    ends_at: datetime
    status: BookingStatus

    room: RoomResponse | None = None
    equipment: list[EquipmentResponse] = Field(default_factory=list)
    participants: list[ParticipantResponseModel] = Field(default_factory=list)

    calendar_synced: bool = False

    @classmethod
    def from_details(cls, details: BookingDetails) -> 'BookingResponse':
        booking = details.booking

        return cls(
            id=booking.identifier,
            title=booking.title,
            description=booking.description,
            organizer_id=booking.organizer_id,
            office_id=booking.office_id,
            series_id=booking.series_id,
            starts_at=booking.starts_at,
            ends_at=booking.ends_at,
            status=booking.status,
            room=RoomResponse.model_validate(details.room) if details.room else None,
            equipment=[EquipmentResponse.model_validate(item) for item in details.equipment],
            participants=[ParticipantResponseModel.model_validate(participant) for participant in details.participants],
            calendar_synced=details.calendar_synced,
        )


class BookingListResponse(APIModel):
    bookings: list[BookingResponse]


class CreateBookingResponse(APIModel):
    series_id: UUID | None = None
    occurrences: list[BookingResponse]


class CancelBookingResponse(APIModel):
    cancelled: int

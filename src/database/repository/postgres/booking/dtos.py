from datetime import UTC
from datetime import datetime
from uuid import UUID

from pydantic import field_validator
from pydantic import model_validator

from src.database.enums import BookingStatus
from src.database.repository.base import BaseModelIdentifiable
from src.database.repository.base import PydanticToORMModelMixin
from src.database.repository.base import TimestampedModelMixin


class Booking(BaseModelIdentifiable, PydanticToORMModelMixin, TimestampedModelMixin):
    title: str
    description: str | None = None

    organizer_id: UUID
    office_id: UUID
    room_id: UUID | None = None
    series_id: UUID | None = None

    starts_at: datetime
    ends_at: datetime

    status: BookingStatus = BookingStatus.active
    cancelled_at: datetime | None = None

    google_event_id: str | None = None
    google_calendar_id: str | None = None

    @field_validator('starts_at', 'ends_at', 'cancelled_at')
    @classmethod
    def require_utc(cls, value: datetime | None) -> datetime | None:
        """
        Everything is stored in UTC.

        A naive datetime reaching this point means a caller forgot to attach the office timezone,
        which would silently shift the booking, so it is rejected rather than assumed.
        """
        if value is None:
            return None

        if value.tzinfo is None:
            msg = 'Booking timestamps must be timezone-aware'
            raise ValueError(msg)

        return value.astimezone(UTC)

    @model_validator(mode='after')
    def validate_window(self) -> 'Booking':
        if self.ends_at <= self.starts_at:
            msg = 'Booking must end after it starts'
            raise ValueError(msg)

        return self

    @property
    def duration_minutes(self) -> int:
        return int((self.ends_at - self.starts_at).total_seconds() // 60)

    @property
    def is_active(self) -> bool:
        return self.status is BookingStatus.active

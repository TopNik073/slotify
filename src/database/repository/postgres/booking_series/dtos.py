from datetime import datetime
from uuid import UUID

from src.database.enums import RecurrenceFrequency
from src.database.repository.base import BaseModelIdentifiable
from src.database.repository.base import PydanticToORMModelMixin
from src.database.repository.base import TimestampedModelMixin


class BookingSeries(BaseModelIdentifiable, PydanticToORMModelMixin, TimestampedModelMixin):
    organizer_id: UUID

    frequency: RecurrenceFrequency
    interval: int = 1
    byweekday: list[int] | None = None

    until: datetime | None = None
    occurrence_count: int | None = None

    rrule: str

    google_event_id: str | None = None
    google_calendar_id: str | None = None

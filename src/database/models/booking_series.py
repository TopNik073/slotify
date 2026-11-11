from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import SmallInteger
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.database.enums import RecurrenceFrequency
from src.database.models.base import BaseORM
from src.database.models.base import TimestampMixin
from src.database.models.base import enum_column


class BookingSeriesORM(BaseORM, TimestampMixin):
    """
    A recurring booking.

    The series stores the recurrence rule; every occurrence is also materialised as its own
    row in ``bookings``. Keeping concrete rows is what lets the exclusion constraints check
    conflicts, and what lets a single occurrence be moved or cancelled without touching the rest.
    """

    __tablename__ = 'booking_series'

    organizer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        index=True,
    )

    frequency: Mapped[RecurrenceFrequency] = mapped_column(enum_column(RecurrenceFrequency, 'recurrence_frequency'))
    interval: Mapped[int] = mapped_column(Integer, default=1)

    # ISO weekdays for a weekly series, 1 = Monday .. 7 = Sunday. Null means "same day as the first occurrence".
    byweekday: Mapped[list[int] | None] = mapped_column(ARRAY(SmallInteger), default=None)

    until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    occurrence_count: Mapped[int | None] = mapped_column(Integer, default=None)

    # RRULE string as sent to Google Calendar, e.g. 'RRULE:FREQ=WEEKLY;BYDAY=MO,WE;COUNT=10'.
    rrule: Mapped[str] = mapped_column(Text)

    google_event_id: Mapped[str | None] = mapped_column(String(1024), default=None)
    google_calendar_id: Mapped[str | None] = mapped_column(String(320), default=None)

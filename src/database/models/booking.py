from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy import literal_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.database.enums import BookingStatus
from src.database.models.base import BaseORM
from src.database.models.base import TimestampMixin
from src.database.models.base import enum_column


class BookingORM(BaseORM, TimestampMixin):
    """
    One concrete reservation of a room, of equipment, or of both.

    ``room_id`` is nullable because movable equipment can be booked on its own; a booking must
    reference a room or at least one piece of equipment, which is enforced in ``BookingService``
    (a check constraint cannot span tables).

    Double booking of a room is prevented by the database, not only by the service: the exclusion
    constraint rejects any two active bookings of the same room whose time ranges overlap, so
    concurrent requests cannot slip through between the availability check and the insert.
    """

    __tablename__ = 'bookings'
    __table_args__ = (
        CheckConstraint('ends_at > starts_at', name='bookings_end_after_start'),
        ExcludeConstraint(
            (literal_column('room_id'), '='),
            (func.tstzrange(literal_column('starts_at'), literal_column('ends_at')), '&&'),
            name='bookings_room_no_overlap',
            using='gist',
            where=literal_column("status = 'active' AND room_id IS NOT NULL"),
        ),
    )

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)

    organizer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        index=True,
    )
    office_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('offices.id', ondelete='CASCADE'),
        index=True,
    )
    room_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('rooms.id', ondelete='CASCADE'),
        default=None,
        index=True,
    )
    series_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('booking_series.id', ondelete='CASCADE'),
        default=None,
        index=True,
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    status: Mapped[BookingStatus] = mapped_column(
        enum_column(BookingStatus, 'booking_status'),
        default=BookingStatus.active,
        index=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    google_event_id: Mapped[str | None] = mapped_column(String(1024), default=None)
    google_calendar_id: Mapped[str | None] = mapped_column(String(320), default=None)

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy import literal_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.database.enums import BookingStatus
from src.database.models.base import BaseORM
from src.database.models.base import enum_column


class BookingEquipmentORM(BaseORM):
    """
    Equipment reserved by a booking.

    ``starts_at``, ``ends_at`` and ``status`` are copies of the parent booking's fields. They are
    denormalised on purpose: an exclusion constraint cannot read another table, so the time window
    has to live here for the database to guarantee that one unit is never booked twice at once.
    ``BookingService`` is the only writer and keeps the copies in sync.
    """

    __tablename__ = 'booking_equipment'
    __table_args__ = (
        UniqueConstraint('booking_id', 'equipment_id', name='booking_equipment_unique'),
        ExcludeConstraint(
            (literal_column('equipment_id'), '='),
            (func.tstzrange(literal_column('starts_at'), literal_column('ends_at')), '&&'),
            name='booking_equipment_no_overlap',
            using='gist',
            where=literal_column("status = 'active'"),
        ),
    )

    booking_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('bookings.id', ondelete='CASCADE'),
        index=True,
    )
    equipment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('equipment.id', ondelete='CASCADE'),
        index=True,
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[BookingStatus] = mapped_column(
        enum_column(BookingStatus, 'booking_status'),
        default=BookingStatus.active,
    )

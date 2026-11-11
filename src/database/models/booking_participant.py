from uuid import UUID

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.database.enums import ParticipantResponse
from src.database.models.base import BaseORM
from src.database.models.base import TimestampMixin
from src.database.models.base import enum_column


class BookingParticipantORM(BaseORM, TimestampMixin):
    """
    Someone invited to a booking.

    ``email`` is always filled and is what gets sent to Google Calendar as an attendee.
    ``user_id`` points at the account behind that address: an existing user when the organizer
    picked them from the directory, or a freshly created ``invited`` placeholder when they typed
    an unknown address. It is nullable only so that deleting a user keeps the attendee list intact.
    """

    __tablename__ = 'booking_participants'
    __table_args__ = (UniqueConstraint('booking_id', 'email', name='booking_participants_unique'),)

    booking_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('bookings.id', ondelete='CASCADE'),
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        default=None,
        index=True,
    )

    email: Mapped[str] = mapped_column(String(320))
    is_organizer: Mapped[bool] = mapped_column(Boolean, default=False)
    response: Mapped[ParticipantResponse] = mapped_column(
        enum_column(ParticipantResponse, 'participant_response'),
        default=ParticipantResponse.needs_action,
    )

from uuid import UUID

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.database.models.base import BaseORM
from src.database.models.base import TimestampMixin


class RoomORM(BaseORM, TimestampMixin):
    __tablename__ = 'rooms'
    __table_args__ = (UniqueConstraint('office_id', 'name', name='rooms_office_name_unique'),)

    office_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('offices.id', ondelete='CASCADE'),
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255))
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    floor: Mapped[str | None] = mapped_column(String(32), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # Deactivated rooms keep their bookings but cannot be booked again.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

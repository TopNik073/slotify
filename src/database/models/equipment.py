from uuid import UUID

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.database.enums import EquipmentType
from src.database.models.base import BaseORM
from src.database.models.base import TimestampMixin
from src.database.models.base import enum_column


class EquipmentORM(BaseORM, TimestampMixin):
    """
    A single piece of equipment, tracked per unit rather than per type.

    ``home_room_id`` is where the unit normally lives. Combined with ``is_movable`` it covers
    both cases: a projector bolted to room A (``is_movable=False``, so it can only be booked
    together with that room), and a camera that travels between rooms (``is_movable=True``,
    bookable with any room of the same office or on its own).
    """

    __tablename__ = 'equipment'

    office_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('offices.id', ondelete='CASCADE'),
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[EquipmentType] = mapped_column(enum_column(EquipmentType, 'equipment_type'))
    inventory_number: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    home_room_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('rooms.id', ondelete='SET NULL'),
        default=None,
        index=True,
    )
    is_movable: Mapped[bool] = mapped_column(Boolean, default=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

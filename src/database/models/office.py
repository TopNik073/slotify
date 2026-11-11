from datetime import time

from sqlalchemy import Boolean
from sqlalchemy import Integer
from sqlalchemy import SmallInteger
from sqlalchemy import String
from sqlalchemy import Time
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.core.config import config
from src.database.models.base import BaseORM
from src.database.models.base import TimestampMixin


class OfficeORM(BaseORM, TimestampMixin):
    """
    A physical location that owns rooms and equipment.

    The office timezone is the single source of truth for working hours and for the booking
    grid shown to users: stored timestamps are always UTC, but a slot only exists if it falls
    inside ``opens_at``/``closes_at`` of a workday in this timezone.
    """

    __tablename__ = 'offices'

    name: Mapped[str] = mapped_column(String(255), unique=True)
    city: Mapped[str] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(512), default=None)

    timezone: Mapped[str] = mapped_column(String(64), default='UTC')

    # ISO weekdays, 1 = Monday .. 7 = Sunday
    workdays: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger), default=lambda: [1, 2, 3, 4, 5])
    opens_at: Mapped[time] = mapped_column(Time, default=time(9, 0))
    closes_at: Mapped[time] = mapped_column(Time, default=time(20, 0))

    slot_minutes: Mapped[int] = mapped_column(Integer, default=config.DEFAULT_SLOT_MINUTES)
    min_booking_minutes: Mapped[int] = mapped_column(Integer, default=config.DEFAULT_MIN_BOOKING_MINUTES)
    max_booking_minutes: Mapped[int] = mapped_column(Integer, default=config.DEFAULT_MAX_BOOKING_MINUTES)
    booking_horizon_days: Mapped[int] = mapped_column(Integer, default=config.DEFAULT_BOOKING_HORIZON_DAYS)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

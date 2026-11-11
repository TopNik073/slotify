from datetime import time
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

from pydantic import Field
from pydantic import field_validator

from src.core.config import config
from src.database.repository.base import BaseModelIdentifiable
from src.database.repository.base import PydanticToORMModelMixin
from src.database.repository.base import TimestampedModelMixin


class Office(BaseModelIdentifiable, PydanticToORMModelMixin, TimestampedModelMixin):
    name: str
    city: str
    address: str | None = None

    timezone: str = 'UTC'

    workdays: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    opens_at: time = time(9, 0)
    closes_at: time = time(20, 0)

    slot_minutes: int = config.DEFAULT_SLOT_MINUTES
    min_booking_minutes: int = config.DEFAULT_MIN_BOOKING_MINUTES
    max_booking_minutes: int = config.DEFAULT_MAX_BOOKING_MINUTES
    booking_horizon_days: int = config.DEFAULT_BOOKING_HORIZON_DAYS

    is_active: bool = True

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            msg = f'Unknown timezone: {value}'
            raise ValueError(msg) from exc

        return value

    @field_validator('workdays')
    @classmethod
    def validate_workdays(cls, value: list[int]) -> list[int]:
        if not value:
            msg = 'An office must have at least one workday'
            raise ValueError(msg)

        if any(day < 1 or day > 7 for day in value):  # noqa: PLR2004
            msg = 'Workdays must be ISO weekdays, 1 (Monday) to 7 (Sunday)'
            raise ValueError(msg)

        return sorted(set(value))

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

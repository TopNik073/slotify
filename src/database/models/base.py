from datetime import UTC
from datetime import datetime
from enum import StrEnum
from uuid import UUID
from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class BaseORM(DeclarativeBase):
    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


_ENUM_TYPES: dict[str, SAEnum] = {}


def enum_column[EnumType: StrEnum](enum_class: type[EnumType], name: str) -> SAEnum:
    """
    Postgres enum type that stores member values rather than member names.

    Types are bound to the shared metadata and memoised by name, so an enum reused across
    tables (``booking_status``) still produces a single ``CREATE TYPE``.
    """
    if name not in _ENUM_TYPES:
        _ENUM_TYPES[name] = SAEnum(
            enum_class,
            name=name,
            values_callable=lambda enum: [member.value for member in enum],
            metadata=BaseORM.metadata,
        )

    return _ENUM_TYPES[name]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update

from src.database.enums import BookingStatus
from src.database.models import BookingEquipmentORM
from src.database.repository.postgres.base import BasePostgresRepository
from src.database.repository.postgres.base import orm_kwargs
from src.database.repository.postgres.booking_equipment.dtos import BookingEquipment


class BookingEquipmentRepository(BasePostgresRepository[BookingEquipmentORM, BookingEquipment]):
    _orm_class = BookingEquipmentORM

    def orm_to_model(self, orm: BookingEquipmentORM) -> BookingEquipment:
        return BookingEquipment.model_validate(orm)

    def model_to_orm(self, model: BookingEquipment) -> BookingEquipmentORM:
        return BookingEquipmentORM(**orm_kwargs(model))

    async def find_conflicts(
        self,
        equipment_ids: list[UUID],
        starts_at: datetime,
        ends_at: datetime,
        *,
        exclude_booking_ids: list[UUID] | None = None,
    ) -> list[BookingEquipment]:
        """Reservations of any of these units that overlap the window."""
        if not equipment_ids:
            return []

        stmt = select(BookingEquipmentORM).where(
            BookingEquipmentORM.equipment_id.in_(equipment_ids),
            BookingEquipmentORM.status == BookingStatus.active,
            BookingEquipmentORM.starts_at < ends_at,
            BookingEquipmentORM.ends_at > starts_at,
        )
        if exclude_booking_ids:
            stmt = stmt.where(BookingEquipmentORM.booking_id.not_in(exclude_booking_ids))

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def list_for_bookings(self, booking_ids: list[UUID]) -> list[BookingEquipment]:
        if not booking_ids:
            return []

        stmt = select(BookingEquipmentORM).where(BookingEquipmentORM.booking_id.in_(booking_ids))
        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def set_for_booking(
        self,
        booking_id: UUID,
        equipment_ids: list[UUID],
        *,
        starts_at: datetime,
        ends_at: datetime,
        status: BookingStatus = BookingStatus.active,
    ) -> list[BookingEquipment]:
        """Replace the equipment attached to a booking with exactly ``equipment_ids``."""
        await self._session.execute(delete(BookingEquipmentORM).where(BookingEquipmentORM.booking_id == booking_id))

        if not equipment_ids:
            await self._session.flush()
            return []

        orms = [
            BookingEquipmentORM(
                booking_id=booking_id,
                equipment_id=equipment_id,
                starts_at=starts_at,
                ends_at=ends_at,
                status=status,
            )
            for equipment_id in dict.fromkeys(equipment_ids)
        ]
        self._session.add_all(orms)
        await self._session.flush()

        return [self.orm_to_model(orm) for orm in orms]

    async def sync_window(self, booking_id: UUID, starts_at: datetime, ends_at: datetime) -> None:
        """Propagate a rescheduled booking to its equipment rows."""
        await self._session.execute(
            update(BookingEquipmentORM)
            .where(BookingEquipmentORM.booking_id == booking_id)
            .values(starts_at=starts_at, ends_at=ends_at)
        )

    async def sync_status(self, booking_ids: list[UUID], status: BookingStatus) -> None:
        """Propagate a cancelled or restored booking to its equipment rows."""
        if not booking_ids:
            return

        await self._session.execute(
            update(BookingEquipmentORM).where(BookingEquipmentORM.booking_id.in_(booking_ids)).values(status=status)
        )

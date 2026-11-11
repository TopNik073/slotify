from datetime import datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy import select

from src.database.enums import BookingStatus
from src.database.models import BookingORM
from src.database.models import BookingParticipantORM
from src.database.repository.postgres.base import BasePostgresRepository
from src.database.repository.postgres.base import orm_kwargs
from src.database.repository.postgres.booking.dtos import Booking


class BookingRepository(BasePostgresRepository[BookingORM, Booking]):
    _orm_class = BookingORM

    def orm_to_model(self, orm: BookingORM) -> Booking:
        return Booking.model_validate(orm)

    def model_to_orm(self, model: Booking) -> BookingORM:
        return BookingORM(**orm_kwargs(model))

    async def find_room_conflicts(
        self,
        room_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        *,
        exclude_booking_ids: list[UUID] | None = None,
    ) -> list[Booking]:
        """
        Active bookings of the room that overlap the window.

        Two bookings overlap when each starts before the other ends; touching edges
        (10:00-11:00 and 11:00-12:00) are not a conflict.
        """
        stmt = select(BookingORM).where(
            BookingORM.room_id == room_id,
            BookingORM.status == BookingStatus.active,
            BookingORM.starts_at < ends_at,
            BookingORM.ends_at > starts_at,
        )
        if exclude_booking_ids:
            stmt = stmt.where(BookingORM.id.not_in(exclude_booking_ids))

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def list_in_range(
        self,
        starts_at: datetime,
        ends_at: datetime,
        *,
        office_id: UUID | None = None,
        room_ids: list[UUID] | None = None,
        only_active: bool = True,
    ) -> list[Booking]:
        """Every booking overlapping the window; backs the availability grid."""
        stmt = (
            select(BookingORM)
            .where(
                BookingORM.starts_at < ends_at,
                BookingORM.ends_at > starts_at,
            )
            .order_by(BookingORM.starts_at)
        )
        if office_id is not None:
            stmt = stmt.where(BookingORM.office_id == office_id)
        if room_ids is not None:
            stmt = stmt.where(BookingORM.room_id.in_(room_ids))
        if only_active:
            stmt = stmt.where(BookingORM.status == BookingStatus.active)

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        starts_after: datetime | None = None,
        ends_before: datetime | None = None,
        only_active: bool = True,
        limit: int | None = None,
    ) -> list[Booking]:
        """Bookings the user organizes plus the ones they were invited to."""
        participates = select(BookingParticipantORM.booking_id).where(BookingParticipantORM.user_id == user_id)
        stmt = (
            select(BookingORM)
            .where(or_(BookingORM.organizer_id == user_id, BookingORM.id.in_(participates)))
            .order_by(BookingORM.starts_at)
        )
        if starts_after is not None:
            stmt = stmt.where(BookingORM.ends_at > starts_after)
        if ends_before is not None:
            stmt = stmt.where(BookingORM.starts_at < ends_before)
        if only_active:
            stmt = stmt.where(BookingORM.status == BookingStatus.active)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def list_by_series(
        self,
        series_id: UUID,
        *,
        starts_after: datetime | None = None,
        only_active: bool = True,
    ) -> list[Booking]:
        stmt = select(BookingORM).where(BookingORM.series_id == series_id).order_by(BookingORM.starts_at)
        if starts_after is not None:
            stmt = stmt.where(BookingORM.starts_at >= starts_after)
        if only_active:
            stmt = stmt.where(BookingORM.status == BookingStatus.active)

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def create_many(self, bookings: list[Booking]) -> list[Booking]:
        """
        Insert a whole recurring series in one transaction.

        The room exclusion constraint applies to the batch as well, so a series that collides
        with itself or with an existing booking fails as a unit instead of leaving half of the
        occurrences behind.
        """
        if not bookings:
            return []

        orms = [self.model_to_orm(booking) for booking in bookings]
        self._session.add_all(orms)
        await self._session.flush()

        return [self.orm_to_model(orm) for orm in orms]

from uuid import UUID

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update

from src.database.enums import ParticipantResponse
from src.database.models import BookingParticipantORM
from src.database.repository.postgres.base import BasePostgresRepository
from src.database.repository.postgres.base import orm_kwargs
from src.database.repository.postgres.booking_participant.dtos import BookingParticipant


class BookingParticipantRepository(BasePostgresRepository[BookingParticipantORM, BookingParticipant]):
    _orm_class = BookingParticipantORM

    def orm_to_model(self, orm: BookingParticipantORM) -> BookingParticipant:
        return BookingParticipant.model_validate(orm)

    def model_to_orm(self, model: BookingParticipant) -> BookingParticipantORM:
        return BookingParticipantORM(**orm_kwargs(model))

    async def list_for_bookings(self, booking_ids: list[UUID]) -> list[BookingParticipant]:
        if not booking_ids:
            return []

        stmt = (
            select(BookingParticipantORM)
            .where(BookingParticipantORM.booking_id.in_(booking_ids))
            .order_by(BookingParticipantORM.is_organizer.desc(), BookingParticipantORM.email)
        )
        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def set_for_booking(
        self,
        booking_id: UUID,
        participants: list[BookingParticipant],
    ) -> list[BookingParticipant]:
        """Replace the attendee list of a booking, keyed by email."""
        await self._session.execute(delete(BookingParticipantORM).where(BookingParticipantORM.booking_id == booking_id))

        unique: dict[str, BookingParticipant] = {}
        for participant in participants:
            unique[participant.email] = participant

        if not unique:
            await self._session.flush()
            return []

        orms = [self.model_to_orm(participant) for participant in unique.values()]
        self._session.add_all(orms)
        await self._session.flush()

        return [self.orm_to_model(orm) for orm in orms]

    async def set_response(
        self,
        booking_id: UUID,
        email: str,
        response: ParticipantResponse,
    ) -> None:
        await self._session.execute(
            update(BookingParticipantORM)
            .where(
                BookingParticipantORM.booking_id == booking_id,
                BookingParticipantORM.email == email.strip().lower(),
            )
            .values(response=response)
        )

    async def link_user_by_email(self, email: str, user_id: UUID) -> None:
        """
        Attach a freshly registered account to the invitations that were waiting for its address.

        Needed because a participant can be invited by email before the account exists.
        """
        await self._session.execute(
            update(BookingParticipantORM)
            .where(
                BookingParticipantORM.email == email.strip().lower(),
                BookingParticipantORM.user_id.is_(None),
            )
            .values(user_id=user_id)
        )

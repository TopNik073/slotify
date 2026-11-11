from typing import Annotated
from uuid import UUID

from fastapi import Depends

from src.database.repository import Booking
from src.database.repository import BookingParticipantRepository
from src.database.repository import User
from src.exceptions import PermissionDenied


class AccessService:
    """
    Who may see and change a booking.

    Rules are deliberately narrow: an admin may do anything, the organizer manages their own
    booking, and an invited participant may read it and answer the invitation but not edit it.
    """

    def __init__(
        self,
        participant_repository: Annotated[BookingParticipantRepository, Depends(BookingParticipantRepository)],
    ):
        self._participant_repository = participant_repository

    @staticmethod
    def ensure_admin(user: User) -> None:
        if not user.is_admin:
            raise PermissionDenied(message='This operation requires administrator rights')

    @staticmethod
    def is_organizer(user: User, booking: Booking) -> bool:
        return booking.organizer_id == user.id

    async def is_participant(self, user: User, booking_id: UUID) -> bool:
        participants = await self._participant_repository.list_for_bookings([booking_id])
        return any(participant.user_id == user.id or participant.email == user.email for participant in participants)

    async def ensure_can_view_booking(self, user: User, booking: Booking) -> None:
        if user.is_admin or self.is_organizer(user, booking):
            return

        if await self.is_participant(user, booking.identifier):
            return

        raise PermissionDenied(message='You do not have access to this booking')

    def ensure_can_modify_booking(self, user: User, booking: Booking) -> None:
        if user.is_admin or self.is_organizer(user, booking):
            return

        raise PermissionDenied(message='Only the organizer can change this booking')

    async def ensure_can_respond_to_booking(self, user: User, booking: Booking) -> None:
        """Answering an invitation is allowed for participants, unlike editing."""
        if self.is_organizer(user, booking):
            return

        if await self.is_participant(user, booking.identifier):
            return

        raise PermissionDenied(message='You were not invited to this booking')

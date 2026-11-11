from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from pydantic import AwareDatetime

from src.database.repository import BookingRepository
from src.database.repository import User
from src.handlers.api.v1.bookings.models import BookingListResponse
from src.handlers.api.v1.bookings.models import BookingResponse
from src.handlers.api.v1.bookings.models import CancelBookingResponse
from src.handlers.dependencies.auth import get_current_admin
from src.services.booking import BookingService

admin_bookings_router = APIRouter(prefix='/bookings', tags=['admin: bookings'])


@admin_bookings_router.get('/', response_model=BookingListResponse)
async def list_bookings(  # noqa: PLR0913, PLR0917
    bookings: Annotated[BookingRepository, Depends()],
    service: Annotated[BookingService, Depends()],
    starts_at: Annotated[AwareDatetime, Query(alias='startsAt')],
    ends_at: Annotated[AwareDatetime, Query(alias='endsAt')],
    office_id: Annotated[UUID | None, Query(alias='officeId')] = None,
    include_cancelled: Annotated[bool, Query(alias='includeCancelled')] = False,
) -> BookingListResponse:
    """Every booking in a window, regardless of who made it."""
    found = await bookings.list_in_range(
        starts_at,
        ends_at,
        office_id=office_id,
        only_active=not include_cancelled,
    )
    details = await service.build_details(found)

    return BookingListResponse(bookings=[BookingResponse.from_details(item) for item in details])


@admin_bookings_router.delete('/{booking_id}', response_model=CancelBookingResponse)
async def cancel_booking(
    booking_id: UUID,
    admin: Annotated[User, Depends(get_current_admin)],
    service: Annotated[BookingService, Depends()],
    whole_series: Annotated[bool, Query(alias='wholeSeries')] = False,
) -> CancelBookingResponse:
    """
    Cancel somebody else's booking, for instance when a room is taken out of service.

    The calendar event is still removed from the organizer's calendar, not the admin's.
    """
    cancelled = await service.cancel(admin, booking_id, whole_series=whole_series)

    return CancelBookingResponse(cancelled=cancelled)

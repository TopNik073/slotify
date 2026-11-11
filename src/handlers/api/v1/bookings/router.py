from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from pydantic import AwareDatetime

from src.database.repository import User
from src.handlers.api.v1.bookings.models import BookingListResponse
from src.handlers.api.v1.bookings.models import BookingResponse
from src.handlers.api.v1.bookings.models import CancelBookingResponse
from src.handlers.api.v1.bookings.models import CreateBookingRequest
from src.handlers.api.v1.bookings.models import CreateBookingResponse
from src.handlers.api.v1.bookings.models import RescheduleBookingRequest
from src.handlers.api.v1.bookings.models import RespondToBookingRequest
from src.handlers.dependencies.auth import get_current_user
from src.services.booking import BookingDraft
from src.services.booking import BookingService
from src.services.booking import RecurrenceDraft

bookings_router = APIRouter(prefix='/bookings', tags=['bookings'])


@bookings_router.post('/', response_model=CreateBookingResponse, status_code=201)
async def create_booking(
    payload: CreateBookingRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BookingService, Depends()],
) -> CreateBookingResponse:
    """
    Book a room, equipment, or both.

    A recurring request returns every occurrence it created. Either all of them are booked or
    none are, so a series never ends up with holes where a room was already taken.
    """
    draft = BookingDraft(
        title=payload.title,
        description=payload.description,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        room_id=payload.room_id,
        equipment_ids=payload.equipment_ids,
        participant_user_ids=payload.participant_user_ids,
        participant_emails=payload.participant_emails,
        recurrence=RecurrenceDraft.model_validate(payload.recurrence, from_attributes=True)
        if payload.recurrence
        else None,
    )

    series = await service.create(user, draft)

    return CreateBookingResponse(
        series_id=series.series_id,
        occurrences=[BookingResponse.from_details(details) for details in series.occurrences],
    )


@bookings_router.get('/', response_model=BookingListResponse)
async def list_my_bookings(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BookingService, Depends()],
    starts_after: Annotated[AwareDatetime | None, Query(alias='startsAfter')] = None,
    ends_before: Annotated[AwareDatetime | None, Query(alias='endsBefore')] = None,
    include_cancelled: Annotated[bool, Query(alias='includeCancelled')] = False,
) -> BookingListResponse:
    """Bookings the user organizes plus the ones they were invited to, upcoming first."""
    bookings = await service.list_mine(
        user,
        starts_after=starts_after,
        ends_before=ends_before,
        include_cancelled=include_cancelled,
    )

    return BookingListResponse(bookings=[BookingResponse.from_details(details) for details in bookings])


@bookings_router.get('/{booking_id}', response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BookingService, Depends()],
) -> BookingResponse:
    return BookingResponse.from_details(await service.get(user, booking_id))


@bookings_router.patch('/{booking_id}', response_model=BookingResponse)
async def reschedule_booking(
    booking_id: UUID,
    payload: RescheduleBookingRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BookingService, Depends()],
) -> BookingResponse:
    details = await service.reschedule(user, booking_id, payload.starts_at, payload.ends_at)

    return BookingResponse.from_details(details)


@bookings_router.delete('/{booking_id}', response_model=CancelBookingResponse)
async def cancel_booking(
    booking_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BookingService, Depends()],
    whole_series: Annotated[bool, Query(alias='wholeSeries')] = False,
) -> CancelBookingResponse:
    """
    Cancel a booking, or with ``wholeSeries=true`` every remaining occurrence of its series.

    Past occurrences are left alone: they already happened.
    """
    cancelled = await service.cancel(user, booking_id, whole_series=whole_series)

    return CancelBookingResponse(cancelled=cancelled)


@bookings_router.post('/{booking_id}/response', status_code=204)
async def respond_to_booking(
    booking_id: UUID,
    payload: RespondToBookingRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BookingService, Depends()],
) -> None:
    """Accept or decline an invitation from inside Slotify, as an alternative to Google's own RSVP."""
    await service.respond(user, booking_id, payload.response)

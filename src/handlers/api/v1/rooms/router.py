from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from pydantic import AwareDatetime

from src.database.repository import RoomRepository
from src.database.repository import User
from src.exceptions import NotFound
from src.handlers.api.v1.rooms.models import AvailabilityResponse
from src.handlers.api.v1.rooms.models import RoomAvailabilityResponse
from src.handlers.api.v1.rooms.models import RoomListResponse
from src.handlers.api.v1.rooms.models import RoomResponse
from src.handlers.api.v1.rooms.models import SlotResponse
from src.handlers.dependencies.auth import get_current_user
from src.services.booking import BookingService

rooms_router = APIRouter(prefix='/rooms', tags=['rooms'])


@rooms_router.get('/', response_model=RoomListResponse)
async def list_rooms(
    _: Annotated[User, Depends(get_current_user)],
    repository: Annotated[RoomRepository, Depends()],
    office_id: Annotated[UUID | None, Query(alias='officeId')] = None,
    min_capacity: Annotated[int | None, Query(alias='minCapacity', ge=1)] = None,
    include_inactive: Annotated[bool, Query(alias='includeInactive')] = False,
) -> RoomListResponse:
    rooms = await repository.list_rooms(
        office_id=office_id,
        min_capacity=min_capacity,
        only_active=not include_inactive,
    )

    return RoomListResponse(rooms=[RoomResponse.model_validate(room) for room in rooms])


@rooms_router.get('/availability', response_model=AvailabilityResponse)
async def get_availability(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[BookingService, Depends()],
    office_id: Annotated[UUID, Query(alias='officeId')],
    day: Annotated[date, Query()],
    min_capacity: Annotated[int | None, Query(alias='minCapacity', ge=1)] = None,
) -> AvailabilityResponse:
    """The booking grid for one local day of an office, slot by slot."""
    availability = await service.get_availability(office_id, day, min_capacity=min_capacity, user=user)

    return AvailabilityResponse(
        office=availability.office,
        day=availability.day,
        rooms=[
            RoomAvailabilityResponse(
                room=RoomResponse.model_validate(entry.room),
                slots=[SlotResponse.model_validate(slot) for slot in entry.slots],
            )
            for entry in availability.rooms
        ],
    )


@rooms_router.get('/free', response_model=RoomListResponse)
async def find_free_rooms(
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[BookingService, Depends()],
    office_id: Annotated[UUID, Query(alias='officeId')],
    starts_at: Annotated[AwareDatetime, Query(alias='startsAt')],
    ends_at: Annotated[AwareDatetime, Query(alias='endsAt')],
    min_capacity: Annotated[int | None, Query(alias='minCapacity', ge=1)] = None,
) -> RoomListResponse:
    rooms = await service.find_free_rooms(office_id, starts_at, ends_at, min_capacity=min_capacity)

    return RoomListResponse(rooms=[RoomResponse.model_validate(room) for room in rooms])


@rooms_router.get('/{room_id}', response_model=RoomResponse)
async def get_room(
    room_id: UUID,
    _: Annotated[User, Depends(get_current_user)],
    repository: Annotated[RoomRepository, Depends()],
) -> RoomResponse:
    room = await repository.get_by_id(room_id)
    if room is None:
        raise NotFound(message='Room not found')

    return RoomResponse.model_validate(room)

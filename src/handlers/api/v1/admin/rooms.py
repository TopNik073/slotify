from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends

from src.database.repository import OfficeRepository
from src.database.repository import Room
from src.database.repository import RoomRepository
from src.exceptions import Conflict
from src.exceptions import NotFound
from src.handlers.api.v1.admin.models import RoomCreateRequest
from src.handlers.api.v1.admin.models import RoomUpdateRequest
from src.handlers.api.v1.rooms.models import RoomResponse

admin_rooms_router = APIRouter(prefix='/rooms', tags=['admin: rooms'])


@admin_rooms_router.post('/', response_model=RoomResponse, status_code=201)
async def create_room(
    payload: RoomCreateRequest,
    rooms: Annotated[RoomRepository, Depends()],
    offices: Annotated[OfficeRepository, Depends()],
) -> RoomResponse:
    if await offices.get_by_id(payload.office_id) is None:
        raise NotFound(message='Office not found')

    if await rooms.get_by_office_and_name(payload.office_id, payload.name) is not None:
        raise Conflict(message='This office already has a room with that name')

    created = await rooms.create(Room.model_validate(payload, from_attributes=True))

    return RoomResponse.model_validate(created)


@admin_rooms_router.patch('/{room_id}', response_model=RoomResponse)
async def update_room(
    room_id: UUID,
    payload: RoomUpdateRequest,
    rooms: Annotated[RoomRepository, Depends()],
) -> RoomResponse:
    room = await rooms.get_by_id(room_id)
    if room is None:
        raise NotFound(message='Room not found')

    changes = payload.model_dump(exclude_unset=True)
    if 'name' in changes:
        clash = await rooms.get_by_office_and_name(room.office_id, changes['name'])
        if clash is not None and clash.identifier != room_id:
            raise Conflict(message='This office already has a room with that name')

    updated = await rooms.update(room.model_copy(update=changes))

    return RoomResponse.model_validate(updated)


@admin_rooms_router.delete('/{room_id}', status_code=204)
async def delete_room(
    room_id: UUID,
    rooms: Annotated[RoomRepository, Depends()],
) -> None:
    """
    Deletes the room and its bookings.

    Equipment installed in it is not deleted, only detached, since the hardware outlives the
    room record.
    """
    if not await rooms.delete(room_id):
        raise NotFound(message='Room not found')

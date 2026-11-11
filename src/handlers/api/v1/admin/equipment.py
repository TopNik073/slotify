from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends

from src.database.repository import Equipment
from src.database.repository import EquipmentRepository
from src.database.repository import OfficeRepository
from src.database.repository import RoomRepository
from src.exceptions import Conflict
from src.exceptions import NotFound
from src.exceptions import ResourceOfficeMismatch
from src.handlers.api.v1.admin.models import EquipmentCreateRequest
from src.handlers.api.v1.admin.models import EquipmentUpdateRequest
from src.handlers.api.v1.equipment.models import EquipmentResponse

admin_equipment_router = APIRouter(prefix='/equipment', tags=['admin: equipment'])


@admin_equipment_router.post('/', response_model=EquipmentResponse, status_code=201)
async def create_equipment(
    payload: EquipmentCreateRequest,
    equipment: Annotated[EquipmentRepository, Depends()],
    offices: Annotated[OfficeRepository, Depends()],
    rooms: Annotated[RoomRepository, Depends()],
) -> EquipmentResponse:
    if await offices.get_by_id(payload.office_id) is None:
        raise NotFound(message='Office not found')

    if payload.home_room_id is not None:
        room = await rooms.get_by_id(payload.home_room_id)
        if room is None:
            raise NotFound(message='Room not found')

        if room.office_id != payload.office_id:
            raise ResourceOfficeMismatch(message='The home room belongs to a different office')

    if payload.inventory_number is not None:
        clash = await equipment.get_by_inventory_number(payload.inventory_number)
        if clash is not None:
            raise Conflict(message='This inventory number is already in use')

    created = await equipment.create(Equipment.model_validate(payload, from_attributes=True))

    return EquipmentResponse.model_validate(created)


@admin_equipment_router.patch('/{equipment_id}', response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: UUID,
    payload: EquipmentUpdateRequest,
    equipment: Annotated[EquipmentRepository, Depends()],
    rooms: Annotated[RoomRepository, Depends()],
) -> EquipmentResponse:
    item = await equipment.get_by_id(equipment_id)
    if item is None:
        raise NotFound(message='Equipment not found')

    changes = payload.model_dump(exclude_unset=True)

    if changes.get('home_room_id') is not None:
        room = await rooms.get_by_id(changes['home_room_id'])
        if room is None:
            raise NotFound(message='Room not found')

        if room.office_id != item.office_id:
            raise ResourceOfficeMismatch(message='The home room belongs to a different office')

    if changes.get('inventory_number') is not None:
        clash = await equipment.get_by_inventory_number(changes['inventory_number'])
        if clash is not None and clash.identifier != equipment_id:
            raise Conflict(message='This inventory number is already in use')

    updated = await equipment.update(item.model_copy(update=changes))

    return EquipmentResponse.model_validate(updated)


@admin_equipment_router.delete('/{equipment_id}', status_code=204)
async def delete_equipment(
    equipment_id: UUID,
    equipment: Annotated[EquipmentRepository, Depends()],
) -> None:
    if not await equipment.delete(equipment_id):
        raise NotFound(message='Equipment not found')

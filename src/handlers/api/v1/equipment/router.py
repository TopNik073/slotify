from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from pydantic import AwareDatetime

from src.database.enums import EquipmentType
from src.database.repository import EquipmentRepository
from src.database.repository import User
from src.exceptions import NotFound
from src.handlers.api.v1.equipment.models import EquipmentListResponse
from src.handlers.api.v1.equipment.models import EquipmentResponse
from src.handlers.dependencies.auth import get_current_user
from src.services.booking import BookingService

equipment_router = APIRouter(prefix='/equipment', tags=['equipment'])


@equipment_router.get('/', response_model=EquipmentListResponse)
async def list_equipment(
    _: Annotated[User, Depends(get_current_user)],
    repository: Annotated[EquipmentRepository, Depends()],
    office_id: Annotated[UUID | None, Query(alias='officeId')] = None,
    room_id: Annotated[UUID | None, Query(alias='roomId')] = None,
    types: Annotated[list[EquipmentType] | None, Query()] = None,
    include_inactive: Annotated[bool, Query(alias='includeInactive')] = False,
) -> EquipmentListResponse:
    """
    ``room_id`` narrows the list to what can actually be used in that room: the units installed
    there plus every movable unit of the office.
    """
    equipment = await repository.list_equipment(
        office_id=office_id,
        room_id=room_id,
        types=types,
        only_active=not include_inactive,
    )

    return EquipmentListResponse(equipment=[EquipmentResponse.model_validate(item) for item in equipment])


@equipment_router.get('/free', response_model=EquipmentListResponse)
async def find_free_equipment(
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[BookingService, Depends()],
    office_id: Annotated[UUID, Query(alias='officeId')],
    starts_at: Annotated[AwareDatetime, Query(alias='startsAt')],
    ends_at: Annotated[AwareDatetime, Query(alias='endsAt')],
    room_id: Annotated[UUID | None, Query(alias='roomId')] = None,
) -> EquipmentListResponse:
    equipment = await service.get_equipment_availability(office_id, starts_at, ends_at, room_id=room_id)

    return EquipmentListResponse(equipment=[EquipmentResponse.model_validate(item) for item in equipment])


@equipment_router.get('/{equipment_id}', response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: UUID,
    _: Annotated[User, Depends(get_current_user)],
    repository: Annotated[EquipmentRepository, Depends()],
) -> EquipmentResponse:
    item = await repository.get_by_id(equipment_id)
    if item is None:
        raise NotFound(message='Equipment not found')

    return EquipmentResponse.model_validate(item)

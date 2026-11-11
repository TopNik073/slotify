from uuid import UUID

from src.database.enums import EquipmentType
from src.handlers.api.models import APIModel


class EquipmentResponse(APIModel):
    id: UUID
    office_id: UUID
    name: str
    type: EquipmentType
    inventory_number: str | None = None
    description: str | None = None
    home_room_id: UUID | None = None
    is_movable: bool
    is_active: bool


class EquipmentListResponse(APIModel):
    equipment: list[EquipmentResponse]

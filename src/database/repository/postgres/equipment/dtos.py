from uuid import UUID

from src.database.enums import EquipmentType
from src.database.repository.base import BaseModelIdentifiable
from src.database.repository.base import PydanticToORMModelMixin
from src.database.repository.base import TimestampedModelMixin


class Equipment(BaseModelIdentifiable, PydanticToORMModelMixin, TimestampedModelMixin):
    office_id: UUID
    name: str
    type: EquipmentType

    inventory_number: str | None = None
    description: str | None = None

    home_room_id: UUID | None = None
    is_movable: bool = True

    is_active: bool = True

    def is_available_in_room(self, room_id: UUID | None) -> bool:
        """
        Fixed equipment can only be used in the room it is installed in.

        Movable units are unrestricted, and so is anything without a home room.
        """
        if self.is_movable or self.home_room_id is None:
            return True

        return room_id == self.home_room_id

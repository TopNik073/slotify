from datetime import datetime
from uuid import UUID

from src.database.enums import BookingStatus
from src.database.repository.base import BaseModelIdentifiable
from src.database.repository.base import PydanticToORMModelMixin


class BookingEquipment(BaseModelIdentifiable, PydanticToORMModelMixin):
    booking_id: UUID
    equipment_id: UUID

    # Mirrors the parent booking; see BookingEquipmentORM for why it is duplicated.
    starts_at: datetime
    ends_at: datetime
    status: BookingStatus = BookingStatus.active

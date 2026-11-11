from uuid import UUID

from src.database.repository.base import BaseModelIdentifiable
from src.database.repository.base import PydanticToORMModelMixin
from src.database.repository.base import TimestampedModelMixin


class Room(BaseModelIdentifiable, PydanticToORMModelMixin, TimestampedModelMixin):
    office_id: UUID
    name: str
    capacity: int = 1
    floor: str | None = None
    description: str | None = None
    is_active: bool = True

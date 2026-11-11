from uuid import UUID

from pydantic import field_validator

from src.database.enums import ParticipantResponse
from src.database.repository.base import BaseModelIdentifiable
from src.database.repository.base import PydanticToORMModelMixin
from src.database.repository.base import TimestampedModelMixin


class BookingParticipant(BaseModelIdentifiable, PydanticToORMModelMixin, TimestampedModelMixin):
    booking_id: UUID
    user_id: UUID | None = None

    email: str
    is_organizer: bool = False
    response: ParticipantResponse = ParticipantResponse.needs_action

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

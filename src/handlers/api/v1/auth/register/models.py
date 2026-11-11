from uuid import UUID

from pydantic import EmailStr
from pydantic import Field

from src.handlers.api.models import APIModel


class RegisterRequest(APIModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

    full_name: str | None = Field(default=None, max_length=255)
    office_id: UUID | None = None


class RegisterResponse(APIModel): ...

from pydantic import EmailStr
from pydantic import Field

from src.handlers.api.models import APIModel


class RestorePasswordRequest(APIModel):
    email: EmailStr
    new_password: str = Field(..., min_length=6)


class RestorePasswordResponse(APIModel): ...

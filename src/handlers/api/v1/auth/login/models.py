from pydantic import EmailStr
from pydantic import Field

from src.handlers.api.models import APIModel


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginResponse(APIModel): ...

from pydantic import EmailStr
from pydantic import Field

from src.handlers.api.models import APIModel
from src.services.auth.models import TokenResponse


class TwoFaRequest(APIModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    code: str = Field(..., min_length=6, max_length=6)


class TwoFaResponse(TokenResponse): ...

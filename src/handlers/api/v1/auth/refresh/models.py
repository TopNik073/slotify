from src.handlers.api.models import APIModel
from src.services.auth.models import TokenResponse


class RefreshRequest(APIModel):
    refresh_token: str


class RefreshResponse(TokenResponse): ...

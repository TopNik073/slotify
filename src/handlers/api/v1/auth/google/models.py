from src.handlers.api.models import APIModel


class GoogleLoginResponse(APIModel):
    authorization_url: str

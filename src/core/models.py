from pydantic import BaseModel
from pydantic import Field
from pydantic import SecretStr


class GoogleCredentialsModel(BaseModel):
    """
    Google OAuth2 client credentials and API endpoints.

    Parsed from environment variables on startup with the ``GOOGLE_CREDENTIALS__`` prefix,
    e.g. ``GOOGLE_CREDENTIALS__CLIENT_ID``, ``GOOGLE_CREDENTIALS__CLIENT_SECRET``.
    """

    client_id: str
    client_secret: SecretStr
    project_id: str | None = None

    redirect_uri: str = 'http://localhost:8000/api/v1/auth/google/callback'

    auth_uri: str = 'https://accounts.google.com/o/oauth2/v2/auth'
    token_uri: str = 'https://oauth2.googleapis.com/token'
    revoke_uri: str = 'https://oauth2.googleapis.com/revoke'
    userinfo_uri: str = 'https://openidconnect.googleapis.com/v1/userinfo'
    calendar_api_base: str = 'https://www.googleapis.com/calendar/v3'

    login_scopes: list[str] = Field(
        default=[
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
        ]
    )
    calendar_scopes: list[str] = Field(
        default=[
            'https://www.googleapis.com/auth/calendar.events',
        ]
    )

    calendar_id: str = 'primary'

    @property
    def scopes(self) -> list[str]:
        return [*self.login_scopes, *self.calendar_scopes]

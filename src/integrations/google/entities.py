from datetime import UTC
from datetime import datetime
from datetime import timedelta

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class GoogleTokenResponse(BaseModel):
    """Response of the OAuth2 token endpoint, for both the code exchange and a refresh."""

    access_token: str
    expires_in: int
    token_type: str = 'Bearer'
    scope: str = ''
    id_token: str | None = None

    # Google only returns a refresh token on the first consent, so a refresh response has none
    # and the previously stored one must be kept.
    refresh_token: str | None = None

    @property
    def expires_at(self) -> datetime:
        return datetime.now(UTC) + timedelta(seconds=self.expires_in)

    @property
    def scopes(self) -> list[str]:
        return self.scope.split() if self.scope else []


class GoogleUserInfo(BaseModel):
    """OpenID Connect userinfo claims."""

    model_config = ConfigDict(populate_by_name=True)

    sub: str
    email: str
    email_verified: bool = False
    name: str | None = None
    picture: str | None = None


class GoogleEventDateTime(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date_time: datetime | None = Field(default=None, alias='dateTime')
    time_zone: str | None = Field(default=None, alias='timeZone')


class GoogleEventAttendee(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str
    display_name: str | None = Field(default=None, alias='displayName')
    organizer: bool = False
    response_status: str = Field(default='needsAction', alias='responseStatus')
    optional: bool = False


class GoogleCalendarEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    status: str | None = None
    summary: str | None = None
    description: str | None = None
    location: str | None = None

    start: GoogleEventDateTime | None = None
    end: GoogleEventDateTime | None = None

    attendees: list[GoogleEventAttendee] = Field(default_factory=list)
    recurrence: list[str] = Field(default_factory=list)

    html_link: str | None = Field(default=None, alias='htmlLink')
    ical_uid: str | None = Field(default=None, alias='iCalUID')

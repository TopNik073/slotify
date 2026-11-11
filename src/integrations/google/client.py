from datetime import datetime
from typing import Any
from urllib.parse import quote

from pydantic import ValidationError

from src.core.config import config
from src.core.logger import get_logger
from src.exceptions import GoogleApiError
from src.integrations.google.entities import GoogleCalendarEvent
from src.integrations.http_client import BaseHTTPClient
from src.integrations.http_client import HTTPClientError

logger = get_logger(__name__)

_NOT_FOUND = 404
_GONE = 410


class GoogleCalendarClient(BaseHTTPClient):
    """
    Google Calendar v3, limited to what a booking needs.

    Every call takes an access token explicitly: events are created on behalf of the organizer,
    so the token belongs to a user rather than to the application.
    """

    def __init__(self) -> None:
        super().__init__(config.google_credentials.calendar_api_base, timeout=15.0)

    @staticmethod
    def _auth(access_token: str) -> dict[str, str]:
        return {'Authorization': f'Bearer {access_token}'}

    @staticmethod
    def _events_path(calendar_id: str, event_id: str | None = None) -> str:
        path = f'/calendars/{quote(calendar_id, safe="")}/events'
        return f'{path}/{quote(event_id, safe="")}' if event_id else path

    async def create_event(
        self,
        access_token: str,
        event: dict[str, Any],
        *,
        calendar_id: str | None = None,
        notify_attendees: bool = True,
    ) -> GoogleCalendarEvent:
        calendar_id = calendar_id or config.google_credentials.calendar_id

        payload = await self._call(
            'POST',
            self._events_path(calendar_id),
            access_token,
            json=event,
            params={'sendUpdates': 'all' if notify_attendees else 'none'},
        )

        return self._parse_event(payload)

    async def update_event(
        self,
        access_token: str,
        event_id: str,
        event: dict[str, Any],
        *,
        calendar_id: str | None = None,
        notify_attendees: bool = True,
    ) -> GoogleCalendarEvent:
        calendar_id = calendar_id or config.google_credentials.calendar_id

        payload = await self._call(
            'PATCH',
            self._events_path(calendar_id, event_id),
            access_token,
            json=event,
            params={'sendUpdates': 'all' if notify_attendees else 'none'},
        )

        return self._parse_event(payload)

    async def delete_event(
        self,
        access_token: str,
        event_id: str,
        *,
        calendar_id: str | None = None,
        notify_attendees: bool = True,
    ) -> None:
        """
        Deleting an event that is already gone is treated as success.

        A user may have removed it from their own calendar; the booking still has to be
        cancellable in Slotify.
        """
        calendar_id = calendar_id or config.google_credentials.calendar_id

        try:
            await self._call(
                'DELETE',
                self._events_path(calendar_id, event_id),
                access_token,
                params={'sendUpdates': 'all' if notify_attendees else 'none'},
            )
        except GoogleApiError as exc:
            if exc.status_code in (_NOT_FOUND, _GONE):
                await logger.awarning('Google event was already deleted', event_id=event_id)
                return

            raise

    async def list_instances(
        self,
        access_token: str,
        event_id: str,
        *,
        time_min: datetime,
        time_max: datetime,
        calendar_id: str | None = None,
    ) -> list[GoogleCalendarEvent]:
        """
        Concrete occurrences of a recurring event within a window.

        Needed to act on a single occurrence: a recurring event has one id, and cancelling or
        moving one of its instances requires that instance's own id.
        """
        calendar_id = calendar_id or config.google_credentials.calendar_id

        payload = await self._call(
            'GET',
            f'{self._events_path(calendar_id, event_id)}/instances',
            access_token,
            params={
                'timeMin': time_min.isoformat(),
                'timeMax': time_max.isoformat(),
            },
        )

        return [self._parse_event(item) for item in payload.get('items', [])]

    async def get_event(
        self,
        access_token: str,
        event_id: str,
        *,
        calendar_id: str | None = None,
    ) -> GoogleCalendarEvent:
        calendar_id = calendar_id or config.google_credentials.calendar_id
        payload = await self._call('GET', self._events_path(calendar_id, event_id), access_token)

        return self._parse_event(payload)

    async def _call(
        self,
        method: str,
        path: str,
        access_token: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict:
        try:
            return await self.request(
                method,  # type: ignore[arg-type]
                path,
                json=json,
                params=params,
                headers=self._auth(access_token),
            )
        except HTTPClientError as exc:
            raise GoogleApiError(
                message=f'Google Calendar: {exc.message}',
                status_code=exc.status_code,
            ) from exc

    @staticmethod
    def _parse_event(payload: dict) -> GoogleCalendarEvent:
        try:
            return GoogleCalendarEvent.model_validate(payload)
        except ValidationError as exc:
            raise GoogleApiError(message='Unexpected Google Calendar response') from exc

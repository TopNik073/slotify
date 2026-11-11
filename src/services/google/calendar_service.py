from datetime import UTC
from datetime import datetime
from datetime import timedelta
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from src.core.logger import get_logger
from src.exceptions import GoogleApiError
from src.exceptions import GoogleCalendarNotConnected
from src.integrations.google import GoogleCalendarClient
from src.integrations.google.entities import GoogleCalendarEvent
from src.services.google.models import CalendarEventDraft
from src.services.google.token_service import GoogleTokenService

logger = get_logger(__name__)


class CalendarService:
    """
    Keeps Google Calendar in step with what happens in Slotify.

    Calendar sync is best effort by design. A booking is a reservation of a physical room, and it
    must not be refused or lost because Google is unreachable or the organizer never connected a
    calendar, so every method reports success instead of raising.
    """

    def __init__(
        self,
        calendar_client: Annotated[GoogleCalendarClient, Depends(GoogleCalendarClient)],
        token_service: Annotated[GoogleTokenService, Depends(GoogleTokenService)],
    ):
        self._client = calendar_client
        self._tokens = token_service

    async def create_event(self, organizer_id: UUID, draft: CalendarEventDraft) -> str | None:
        """The id of the created event, or None when it could not be created."""
        token = await self._access_token(organizer_id)
        if token is None:
            return None

        try:
            event = await self._create_or_get_event(token, draft)
        except GoogleApiError as exc:
            await logger.aerror(
                'Could not create a Google Calendar event',
                organizer_id=str(organizer_id),
                error=exc.message,
            )
            return None

        await logger.ainfo(
            'Google Calendar event published or reconciled',
            organizer_id=str(organizer_id),
            event_id=event.id,
        )
        return event.id

    async def _create_or_get_event(self, token: str, draft: CalendarEventDraft) -> GoogleCalendarEvent:
        try:
            return await self._client.create_event(token, draft.to_google_payload())
        except GoogleApiError as exc:
            uncertain_result = exc.status_code is None or exc.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
            if draft.event_id is None or not (uncertain_result or exc.status_code == HTTPStatus.CONFLICT):
                raise

            # A previous attempt may have succeeded before its response was lost. Read the
            # existing event instead of generating a new id and notifying the guests again.
            try:
                event = await self._client.get_event(token, draft.event_id)
            except GoogleApiError:
                raise exc from None
            if event.status == 'cancelled':
                raise GoogleApiError(message='The Google Calendar event was cancelled', status_code=410) from exc
            return event

    async def update_event(self, organizer_id: UUID, event_id: str, draft: CalendarEventDraft) -> bool:
        token = await self._access_token(organizer_id)
        if token is None:
            return False

        try:
            await self._client.update_event(token, event_id, draft.to_google_payload(include_id=False))
        except GoogleApiError as exc:
            await logger.aerror(
                'Could not update a Google Calendar event',
                organizer_id=str(organizer_id),
                event_id=event_id,
                error=exc.message,
            )
            return False

        return True

    async def cancel_occurrence(
        self,
        organizer_id: UUID,
        event_id: str,
        starts_at: datetime,
        ends_at: datetime,
    ) -> bool:
        """
        Cancel a single occurrence of a recurring event, leaving the rest of the series alone.

        Google models this as patching the instance that covers the window, not the series.
        """
        token = await self._access_token(organizer_id)
        if token is None:
            return False

        try:
            instances = await self._client.list_instances(
                token,
                event_id,
                time_min=starts_at - timedelta(minutes=1),
                time_max=ends_at + timedelta(minutes=1),
            )
            target = next(
                (
                    instance
                    for instance in instances
                    if instance.start
                    and instance.start.date_time
                    and instance.start.date_time.astimezone(UTC) == starts_at.astimezone(UTC)
                ),
                None,
            )
            if target is None:
                await logger.awarning(
                    'No Google instance matches this occurrence',
                    event_id=event_id,
                    starts_at=starts_at.isoformat(),
                )
                return False

            await self._client.update_event(token, target.id, {'status': 'cancelled'})
        except GoogleApiError as exc:
            await logger.aerror(
                'Could not cancel a Google Calendar occurrence',
                event_id=event_id,
                error=exc.message,
            )
            return False

        return True

    async def delete_event(self, organizer_id: UUID, event_id: str) -> bool:
        token = await self._access_token(organizer_id)
        if token is None:
            return False

        try:
            await self._client.delete_event(token, event_id)
        except GoogleApiError as exc:
            await logger.aerror(
                'Could not delete a Google Calendar event',
                organizer_id=str(organizer_id),
                event_id=event_id,
                error=exc.message,
            )
            return False

        return True

    async def is_connected(self, user_id: UUID) -> bool:
        account = await self._tokens.get_account(user_id)
        return account is not None and account.calendar_connected

    async def _access_token(self, organizer_id: UUID) -> str | None:
        try:
            return await self._tokens.get_access_token(organizer_id)
        except GoogleCalendarNotConnected:
            await logger.ainfo('Organizer has no connected calendar, skipping sync', user_id=str(organizer_id))
            return None
        except GoogleApiError as exc:
            await logger.aerror('Could not obtain a Google access token', error=exc.message)
            return None

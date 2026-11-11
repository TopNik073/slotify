from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class CalendarEventDraft(BaseModel):
    """
    A calendar event described in neutral terms.

    The calendar service deliberately does not know about bookings: callers translate their own
    aggregate into this shape, which keeps the Google layer independent of the booking domain.
    """

    title: str
    # Stable identity supplied by the caller, so retrying publication cannot create a new event.
    event_id: str | None = Field(default=None, pattern=r'^[0-9a-v]{5,1024}$')
    description: str | None = None
    location: str | None = None

    starts_at: datetime
    ends_at: datetime
    timezone: str

    attendee_emails: list[str] = Field(default_factory=list)
    organizer_email: str | None = None

    # iCalendar RRULE line for a recurring event, e.g. 'RRULE:FREQ=WEEKLY;COUNT=10'.
    recurrence: str | None = None

    def to_google_payload(self, *, include_id: bool = True) -> dict:
        payload: dict = {
            'summary': self.title,
            'start': {
                'dateTime': self.starts_at.isoformat(),
                'timeZone': self.timezone,
            },
            'end': {
                'dateTime': self.ends_at.isoformat(),
                'timeZone': self.timezone,
            },
        }

        if include_id and self.event_id:
            payload['id'] = self.event_id

        if self.description:
            payload['description'] = self.description

        if self.location:
            payload['location'] = self.location

        if self.attendee_emails:
            emails = dict.fromkeys(email.strip().lower() for email in self.attendee_emails)
            payload['attendees'] = [{'email': email} for email in emails]

        if self.recurrence:
            payload['recurrence'] = [self.recurrence]

        return payload

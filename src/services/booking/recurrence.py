from datetime import UTC
from datetime import datetime
from itertools import islice

from dateutil.rrule import DAILY
from dateutil.rrule import WEEKLY
from dateutil.rrule import rrule

from src.core.config import config
from src.database.enums import RecurrenceFrequency
from src.database.repository import Office
from src.exceptions import RecurrenceNotAllowed

_FREQUENCIES = {
    RecurrenceFrequency.daily: DAILY,
    RecurrenceFrequency.weekly: WEEKLY,
}

# dateutil counts weekdays from 0 = Monday; the API speaks ISO weekdays, 1 = Monday.
_ICAL_WEEKDAYS = ('MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU')


class Recurrence:
    """
    Expands a recurrence rule into concrete booking windows.

    Occurrences are generated in office-local time, not in UTC. A weekly 10:00 meeting has to
    stay at 10:00 after a daylight saving change, which it would not if the rule advanced by a
    fixed 7 x 24 hours.
    """

    def __init__(  # noqa: PLR0913
        self,
        office: Office,
        frequency: RecurrenceFrequency,
        *,
        interval: int = 1,
        byweekday: list[int] | None = None,
        until: datetime | None = None,
        count: int | None = None,
    ):
        if interval < 1:
            raise RecurrenceNotAllowed(message='Recurrence interval must be at least 1')

        if until is None and count is None:
            raise RecurrenceNotAllowed(message='A recurring booking needs an end date or a number of repeats')

        if byweekday and any(day < 1 or day > 7 for day in byweekday):  # noqa: PLR2004
            raise RecurrenceNotAllowed(message='Weekdays must be ISO weekdays, 1 (Monday) to 7 (Sunday)')

        self._office = office
        self._frequency = frequency
        self._interval = interval
        self._byweekday = sorted(set(byweekday)) if byweekday else None
        self._until = until
        self._count = count

    def expand(self, starts_at: datetime, ends_at: datetime) -> list[tuple[datetime, datetime]]:
        """
        All occurrences of a series whose first window is ``starts_at``-``ends_at``.

        The duration is kept in local wall-clock terms so every occurrence has the same start and
        end time on the clock, which is what a user who booked 10:00-11:00 expects.
        """
        zone = self._office.zone
        local_start = starts_at.astimezone(zone).replace(tzinfo=None)
        local_end = ends_at.astimezone(zone).replace(tzinfo=None)
        duration = local_end - local_start

        rule = rrule(
            freq=_FREQUENCIES[self._frequency],
            dtstart=local_start,
            interval=self._interval,
            byweekday=[day - 1 for day in self._byweekday] if self._byweekday else None,
            until=self._until.astimezone(zone).replace(tzinfo=None) if self._until else None,
            count=self._count,
        )

        limit = config.MAX_SERIES_OCCURRENCES
        occurrences = list(islice(rule, limit + 1))

        if not occurrences:
            raise RecurrenceNotAllowed(message='This recurrence rule produces no occurrences')

        if len(occurrences) > limit:
            raise RecurrenceNotAllowed(message=f'A series may contain at most {limit} occurrences')

        windows: list[tuple[datetime, datetime]] = []
        for occurrence in occurrences:
            occurrence_start = occurrence.replace(tzinfo=zone)
            occurrence_end = (occurrence + duration).replace(tzinfo=zone)
            windows.append((occurrence_start.astimezone(UTC), occurrence_end.astimezone(UTC)))

        return windows

    def to_rrule_string(self) -> str:
        """The rule in iCalendar form, as Google Calendar expects it in ``recurrence``."""
        parts = [f'FREQ={self._frequency.value.upper()}']

        if self._interval != 1:
            parts.append(f'INTERVAL={self._interval}')

        if self._byweekday:
            days = ','.join(_ICAL_WEEKDAYS[day - 1] for day in self._byweekday)
            parts.append(f'BYDAY={days}')

        if self._count is not None:
            parts.append(f'COUNT={self._count}')

        if self._until is not None:
            # Google requires the UTC basic format with a trailing Z.
            parts.append(f'UNTIL={self._until.astimezone(UTC):%Y%m%dT%H%M%SZ}')

        return f'RRULE:{";".join(parts)}'

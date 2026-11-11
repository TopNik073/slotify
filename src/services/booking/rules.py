from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta

from src.database.repository import Office
from src.exceptions import BookingDurationNotAllowed
from src.exceptions import BookingInPast
from src.exceptions import BookingTooFarAhead
from src.exceptions import InvalidBookingWindow
from src.exceptions import OutsideWorkingHours
from src.exceptions import SlotNotAligned


class BookingRules:
    """
    The booking policy of one office.

    Every check is done in the office timezone, which is the only place local time exists:
    stored timestamps are UTC, and the same UTC instant is inside working hours for one office
    and outside for another.
    """

    def __init__(self, office: Office):
        self._office = office

    @property
    def office(self) -> Office:
        return self._office

    def to_local(self, moment: datetime) -> datetime:
        return moment.astimezone(self._office.zone)

    def working_window(self, day: date) -> tuple[datetime, datetime] | None:
        """Opening and closing instants of a local calendar day, or None if the office is closed."""
        if day.isoweekday() not in self._office.workdays:
            return None

        opens = datetime.combine(day, self._office.opens_at, tzinfo=self._office.zone)
        closes = datetime.combine(day, self._office.closes_at, tzinfo=self._office.zone)

        return opens, closes

    def iter_slots(self, day: date) -> list[tuple[datetime, datetime]]:
        """The grid of bookable slots for a local day, as UTC instants."""
        window = self.working_window(day)
        if window is None:
            return []

        opens, closes = window
        step = timedelta(minutes=self._office.slot_minutes)

        slots: list[tuple[datetime, datetime]] = []
        cursor = opens
        while cursor + step <= closes:
            slots.append((cursor.astimezone(UTC), (cursor + step).astimezone(UTC)))
            cursor += step

        return slots

    def validate(
        self,
        starts_at: datetime,
        ends_at: datetime,
        *,
        now: datetime | None = None,
    ) -> None:
        """Raise the specific ClientError describing why this window cannot be booked."""
        now = now or datetime.now(UTC)

        if ends_at <= starts_at:
            raise InvalidBookingWindow

        if starts_at < now:
            raise BookingInPast

        horizon = now + timedelta(days=self._office.booking_horizon_days)
        if starts_at > horizon:
            raise BookingTooFarAhead(
                message=f'This office allows booking at most {self._office.booking_horizon_days} days ahead'
            )

        self._validate_duration(starts_at, ends_at)
        self._validate_working_hours(starts_at, ends_at)
        self._validate_alignment(starts_at, ends_at)

    def _validate_duration(self, starts_at: datetime, ends_at: datetime) -> None:
        minutes = int((ends_at - starts_at).total_seconds() // 60)
        office = self._office

        if minutes < office.min_booking_minutes or minutes > office.max_booking_minutes:
            raise BookingDurationNotAllowed(
                message=(
                    f'Booking must last between {office.min_booking_minutes} and {office.max_booking_minutes} minutes'
                )
            )

    def _validate_working_hours(self, starts_at: datetime, ends_at: datetime) -> None:
        local_start = self.to_local(starts_at)
        local_end = self.to_local(ends_at)

        if local_start.date() != local_end.date():
            raise OutsideWorkingHours(message='A booking cannot span more than one day')

        window = self.working_window(local_start.date())
        if window is None:
            raise OutsideWorkingHours(message='The office is closed on this day')

        opens, closes = window
        if local_start < opens or local_end > closes:
            raise OutsideWorkingHours(
                message=(
                    f'The office is open from {self._office.opens_at:%H:%M} '
                    f'to {self._office.closes_at:%H:%M} local time'
                )
            )

    def _validate_alignment(self, starts_at: datetime, ends_at: datetime) -> None:
        """
        Both edges must sit on the slot grid.

        The grid is anchored at opening time rather than midnight, so an office opening at 09:15
        with 30-minute slots offers 09:15, 09:45, ... instead of an unreachable 09:00.
        """
        local_start = self.to_local(starts_at)
        window = self.working_window(local_start.date())
        if window is None:
            raise OutsideWorkingHours(message='The office is closed on this day')

        opens, _ = window
        slot = timedelta(minutes=self._office.slot_minutes)

        for edge in (starts_at, ends_at):
            offset = self.to_local(edge) - opens
            if offset % slot:
                raise SlotNotAligned(
                    message=f'Booking must start and end on a {self._office.slot_minutes}-minute boundary'
                )

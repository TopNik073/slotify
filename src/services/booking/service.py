from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import Depends
from sqlalchemy.exc import IntegrityError

from src.core.config import config
from src.core.logger import get_logger
from src.database.enums import BookingStatus
from src.database.enums import ParticipantResponse
from src.database.enums import UserStatus
from src.database.repository import Booking
from src.database.repository import BookingParticipant
from src.database.repository import BookingParticipantRepository
from src.database.repository import BookingRepository
from src.database.repository import BookingSeries
from src.database.repository import BookingSeriesRepository
from src.database.repository import Equipment
from src.database.repository import EquipmentRepository
from src.database.repository import Office
from src.database.repository import OfficeRepository
from src.database.repository import Room
from src.database.repository import RoomRepository
from src.database.repository import User
from src.database.repository import UserRepository
from src.database.repository.postgres.booking_equipment import BookingEquipmentRepository
from src.exceptions import BookingConflict
from src.exceptions import EquipmentNotMovable
from src.exceptions import NotFound
from src.exceptions import NothingToBook
from src.exceptions import ResourceInactive
from src.exceptions import ResourceOfficeMismatch
from src.services.access import AccessService
from src.services.booking.models import BookingDetails
from src.services.booking.models import BookingDraft
from src.services.booking.models import OfficeDayAvailability
from src.services.booking.models import RoomAvailability
from src.services.booking.models import SeriesDetails
from src.services.booking.models import SlotAvailability
from src.services.booking.recurrence import Recurrence
from src.services.booking.rules import BookingRules
from src.services.google import CalendarEventDraft
from src.services.google import CalendarService
from src.services.ses import YandexSESService

logger = get_logger(__name__)

Window = tuple[datetime, datetime]


class BookingService:
    """
    Creating, moving and cancelling reservations of rooms and equipment.

    Validation happens in two layers that are both necessary. The service checks the office
    policy and reports precisely what is wrong, which the database cannot do; the database
    enforces non-overlap, which the service cannot do safely because two concurrent requests
    would both pass their checks before either inserts.
    """

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        office_repository: Annotated[OfficeRepository, Depends(OfficeRepository)],
        room_repository: Annotated[RoomRepository, Depends(RoomRepository)],
        equipment_repository: Annotated[EquipmentRepository, Depends(EquipmentRepository)],
        booking_repository: Annotated[BookingRepository, Depends(BookingRepository)],
        booking_equipment_repository: Annotated[BookingEquipmentRepository, Depends(BookingEquipmentRepository)],
        participant_repository: Annotated[BookingParticipantRepository, Depends(BookingParticipantRepository)],
        series_repository: Annotated[BookingSeriesRepository, Depends(BookingSeriesRepository)],
        user_repository: Annotated[UserRepository, Depends(UserRepository)],
        access_service: Annotated[AccessService, Depends(AccessService)],
        calendar_service: Annotated[CalendarService, Depends(CalendarService)],
        email_service: Annotated[YandexSESService, Depends(YandexSESService)],
    ):
        self._offices = office_repository
        self._rooms = room_repository
        self._equipment = equipment_repository
        self._bookings = booking_repository
        self._booking_equipment = booking_equipment_repository
        self._participants = participant_repository
        self._series = series_repository
        self._users = user_repository
        self._access = access_service
        self._calendar = calendar_service
        self._email = email_service

    # --------- AVAILABILITY ---------
    async def get_availability(
        self,
        office_id: UUID,
        day: date,
        *,
        room_ids: list[UUID] | None = None,
        min_capacity: int | None = None,
        user: User | None = None,
    ) -> OfficeDayAvailability:
        """The slot grid of every room of an office for one local day, each slot marked free or taken."""
        office = await self._require_office(office_id)
        rules = BookingRules(office)

        rooms = await self._rooms.list_rooms(office_id=office_id, min_capacity=min_capacity)
        if room_ids is not None:
            wanted = set(room_ids)
            rooms = [room for room in rooms if room.identifier in wanted]

        slots = rules.iter_slots(day)
        if not slots or not rooms:
            return OfficeDayAvailability(office=office, day=day, rooms=[])

        day_start, day_end = slots[0][0], slots[-1][1]
        bookings = await self._bookings.list_in_range(
            day_start,
            day_end,
            office_id=office_id,
            room_ids=[room.identifier for room in rooms],
        )

        my_booking_ids: set[UUID] = set()
        if user is not None and bookings:
            my_booking_ids = {booking.identifier for booking in bookings if booking.organizer_id == user.identifier}
            other_booking_ids = [booking.identifier for booking in bookings if booking.identifier not in my_booking_ids]
            # One batch for the whole day; do not load attendees separately for each room or slot.
            if other_booking_ids:
                participants = await self._participants.list_for_bookings(other_booking_ids)
                my_booking_ids.update(
                    participant.booking_id
                    for participant in participants
                    if (participant.user_id == user.identifier or participant.email == user.email)
                    and participant.response != ParticipantResponse.declined
                )

        taken: dict[UUID, list[Booking]] = {}
        for booking in bookings:
            if booking.room_id is not None:
                taken.setdefault(booking.room_id, []).append(booking)

        return OfficeDayAvailability(
            office=office,
            day=day,
            rooms=[
                RoomAvailability(
                    room=room,
                    slots=self._mark_slots(slots, taken.get(room.identifier, []), my_booking_ids=my_booking_ids),
                )
                for room in rooms
            ],
        )

    @staticmethod
    def _mark_slots(
        slots: list[Window],
        bookings: list[Booking],
        *,
        my_booking_ids: set[UUID] | None = None,
    ) -> list[SlotAvailability]:
        marked: list[SlotAvailability] = []
        my_booking_ids = my_booking_ids or set()

        for slot_start, slot_end in slots:
            blocking = next(
                (booking for booking in bookings if booking.starts_at < slot_end and booking.ends_at > slot_start),
                None,
            )
            marked.append(
                SlotAvailability(
                    starts_at=slot_start,
                    ends_at=slot_end,
                    is_free=blocking is None,
                    booking_id=blocking.id if blocking else None,
                    is_mine=blocking is not None and blocking.identifier in my_booking_ids,
                )
            )

        return marked

    async def find_free_rooms(
        self,
        office_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        *,
        min_capacity: int | None = None,
    ) -> list[Room]:
        """Rooms of an office with nothing booked in the window; the window itself must be bookable."""
        office = await self._require_office(office_id)
        BookingRules(office).validate(starts_at, ends_at)

        rooms = await self._rooms.list_rooms(office_id=office_id, min_capacity=min_capacity)
        if not rooms:
            return []

        bookings = await self._bookings.list_in_range(
            starts_at,
            ends_at,
            office_id=office_id,
            room_ids=[room.identifier for room in rooms],
        )
        busy = {booking.room_id for booking in bookings if booking.room_id is not None}

        return [room for room in rooms if room.identifier not in busy]

    async def get_equipment_availability(
        self,
        office_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        *,
        room_id: UUID | None = None,
    ) -> list[Equipment]:
        """Equipment of an office that is free for the whole window and usable in the given room."""
        candidates = await self._equipment.list_equipment(office_id=office_id, room_id=room_id)
        if not candidates:
            return []

        conflicts = await self._booking_equipment.find_conflicts(
            [item.identifier for item in candidates],
            starts_at,
            ends_at,
        )
        busy = {conflict.equipment_id for conflict in conflicts}

        return [item for item in candidates if item.identifier not in busy]

    # --------- CREATE ---------
    async def create(self, organizer: User, draft: BookingDraft) -> SeriesDetails:
        office, room, equipment = await self._resolve_resources(draft)
        rules = BookingRules(office)

        recurrence = self._build_recurrence(office, draft)
        windows = (
            recurrence.expand(draft.starts_at, draft.ends_at) if recurrence else [(draft.starts_at, draft.ends_at)]
        )

        for starts_at, ends_at in windows:
            rules.validate(starts_at, ends_at)

        await self._assert_free(room, equipment, windows)

        series: BookingSeries | None = None
        if recurrence:
            series = await self._series.create(
                BookingSeries(
                    organizer_id=organizer.identifier,
                    frequency=draft.recurrence.frequency,  # type: ignore[union-attr]
                    interval=draft.recurrence.interval,  # type: ignore[union-attr]
                    byweekday=draft.recurrence.byweekday,  # type: ignore[union-attr]
                    until=draft.recurrence.until,  # type: ignore[union-attr]
                    occurrence_count=draft.recurrence.count,  # type: ignore[union-attr]
                    rrule=recurrence.to_rrule_string(),
                )
            )

        participants = await self._resolve_participants(organizer, draft, office)

        drafts = [
            Booking(
                title=draft.title,
                description=draft.description,
                organizer_id=organizer.identifier,
                office_id=office.identifier,
                room_id=room.identifier if room else None,
                series_id=series.identifier if series else None,
                starts_at=starts_at,
                ends_at=ends_at,
            )
            for starts_at, ends_at in windows
        ]

        created = await self._insert(drafts, equipment, participants)

        event_id = await self._publish_to_calendar(
            organizer=organizer,
            office=office,
            room=room,
            equipment=equipment,
            booking=created[0],
            attendee_emails=list(participants),
            rrule=recurrence.to_rrule_string() if recurrence else None,
        )

        if event_id:
            created = await self._attach_event_id(created, series, event_id)

        # Google owns the calendar invitation. Slotify only helps placeholder users register,
        # including when Google's creation result is unknown after a lost response.
        await self._notify_invited(organizer, participants)

        return SeriesDetails(
            series_id=series.identifier if series else None,
            occurrences=[
                BookingDetails(
                    booking=booking,
                    room=room,
                    equipment=equipment,
                    participants=await self._participants.list_for_bookings([booking.identifier]),
                    calendar_synced=event_id is not None,
                )
                for booking in created
            ],
        )

    async def _insert(
        self,
        drafts: list[Booking],
        equipment: list[Equipment],
        participants: dict[str, UUID | None],
    ) -> list[Booking]:
        """
        Write the booking, its equipment and its attendees as one unit.

        An ``IntegrityError`` here is almost always an exclusion constraint firing, which means
        another request booked the same room or unit in the meantime.
        """
        equipment_ids = [item.identifier for item in equipment]

        try:
            created = await self._bookings.create_many(drafts)

            for booking in created:
                if equipment_ids:
                    await self._booking_equipment.set_for_booking(
                        booking.identifier,
                        equipment_ids,
                        starts_at=booking.starts_at,
                        ends_at=booking.ends_at,
                    )

                await self._participants.set_for_booking(
                    booking.identifier,
                    [
                        BookingParticipant(
                            booking_id=booking.identifier,
                            user_id=user_id,
                            email=email,
                            is_organizer=index == 0,
                            response=ParticipantResponse.accepted if index == 0 else ParticipantResponse.needs_action,
                        )
                        for index, (email, user_id) in enumerate(participants.items())
                    ],
                )
        except IntegrityError as exc:
            await logger.awarning('Booking rejected by a database constraint', error=str(exc.orig))
            raise BookingConflict from exc

        return created

    async def _attach_event_id(
        self,
        bookings: list[Booking],
        series: BookingSeries | None,
        event_id: str,
    ) -> list[Booking]:
        calendar_id = config.google_credentials.calendar_id

        if series is not None:
            series.google_event_id = event_id
            series.google_calendar_id = calendar_id
            await self._series.update(series)

        updated: list[Booking] = []
        for booking in bookings:
            booking.google_event_id = event_id
            booking.google_calendar_id = calendar_id
            updated.append(await self._bookings.update(booking))

        return updated

    # --------- READ ---------
    async def get(self, user: User, booking_id: UUID) -> BookingDetails:
        booking = await self._require_booking(booking_id)
        await self._access.ensure_can_view_booking(user, booking)

        return (await self.build_details([booking]))[0]

    async def list_mine(
        self,
        user: User,
        *,
        starts_after: datetime | None = None,
        ends_before: datetime | None = None,
        include_cancelled: bool = False,
    ) -> list[BookingDetails]:
        bookings = await self._bookings.list_for_user(
            user.identifier,
            starts_after=starts_after or datetime.now(UTC),
            ends_before=ends_before,
            only_active=not include_cancelled,
        )

        return await self.build_details(bookings)

    async def build_details(self, bookings: list[Booking]) -> list[BookingDetails]:
        """Resolve rooms, equipment and attendees for a page of bookings without a query per row."""
        if not bookings:
            return []

        booking_ids = [booking.identifier for booking in bookings]

        room_ids = list({booking.room_id for booking in bookings if booking.room_id})
        rooms = {room.identifier: room for room in await self._rooms.get_by_ids(room_ids)}

        links = await self._booking_equipment.list_for_bookings(booking_ids)
        equipment = {
            item.identifier: item
            for item in await self._equipment.get_by_ids(list({link.equipment_id for link in links}))
        }
        equipment_by_booking: dict[UUID, list[Equipment]] = {}
        for link in links:
            item = equipment.get(link.equipment_id)
            if item is not None:
                equipment_by_booking.setdefault(link.booking_id, []).append(item)

        participants = await self._participants.list_for_bookings(booking_ids)
        participants_by_booking: dict[UUID, list[BookingParticipant]] = {}
        for participant in participants:
            participants_by_booking.setdefault(participant.booking_id, []).append(participant)

        return [
            BookingDetails(
                booking=booking,
                room=rooms.get(booking.room_id) if booking.room_id else None,
                equipment=equipment_by_booking.get(booking.identifier, []),
                participants=participants_by_booking.get(booking.identifier, []),
                calendar_synced=booking.google_event_id is not None,
            )
            for booking in bookings
        ]

    # --------- MODIFY ---------
    async def reschedule(
        self,
        user: User,
        booking_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
    ) -> BookingDetails:
        booking = await self._require_booking(booking_id)
        self._access.ensure_can_modify_booking(user, booking)

        if booking.status is not BookingStatus.active:
            raise NotFound(message='This booking is cancelled')

        office = await self._require_office(booking.office_id)
        BookingRules(office).validate(starts_at, ends_at)

        room = await self._rooms.get_by_id(booking.room_id) if booking.room_id else None
        links = await self._booking_equipment.list_for_bookings([booking.identifier])
        equipment = await self._equipment.get_by_ids([link.equipment_id for link in links])

        await self._assert_free(room, equipment, [(starts_at, ends_at)], exclude_booking_ids=[booking.identifier])

        booking.starts_at = starts_at
        booking.ends_at = ends_at

        try:
            booking = await self._bookings.update(booking)
            await self._booking_equipment.sync_window(booking.identifier, starts_at, ends_at)
        except IntegrityError as exc:
            await logger.awarning('Reschedule rejected by a database constraint', error=str(exc.orig))
            raise BookingConflict from exc

        await self._update_calendar(user, office, room, equipment, booking)

        return (await self.build_details([booking]))[0]

    async def cancel(self, user: User, booking_id: UUID, *, whole_series: bool = False) -> int:
        """Cancel one booking or every remaining occurrence of its series; returns how many were cancelled."""
        booking = await self._require_booking(booking_id)
        self._access.ensure_can_modify_booking(user, booking)

        targets = [booking]
        if whole_series and booking.series_id is not None:
            targets = await self._bookings.list_by_series(booking.series_id, starts_after=datetime.now(UTC))
            if not any(target.identifier == booking.identifier for target in targets):
                targets.append(booking)

        cancelled_at = datetime.now(UTC)
        for target in targets:
            if target.status is not BookingStatus.active:
                continue

            target.status = BookingStatus.cancelled
            target.cancelled_at = cancelled_at
            await self._bookings.update(target)

        await self._booking_equipment.sync_status(
            [target.identifier for target in targets],
            BookingStatus.cancelled,
        )

        await self._withdraw_from_calendar(user, booking, whole_series=whole_series)

        return len(targets)

    async def respond(self, user: User, booking_id: UUID, response: ParticipantResponse) -> None:
        booking = await self._require_booking(booking_id)
        await self._access.ensure_can_respond_to_booking(user, booking)

        await self._participants.set_response(booking.identifier, user.email, response)

    # --------- RESOURCE RESOLUTION ---------
    async def _resolve_resources(self, draft: BookingDraft) -> tuple[Office, Room | None, list[Equipment]]:
        room: Room | None = None
        if draft.room_id is not None:
            room = await self._rooms.get_by_id(draft.room_id)
            if room is None:
                raise NotFound(message='Room not found')

        equipment = await self._equipment.get_by_ids(draft.equipment_ids)
        if len(equipment) != len(set(draft.equipment_ids)):
            raise NotFound(message='Some of the requested equipment does not exist')

        if room is None and not equipment:
            raise NothingToBook

        if room is not None and not room.is_active:
            raise ResourceInactive(message=f'Room {room.name} is not available for booking')

        inactive = next((item for item in equipment if not item.is_active), None)
        if inactive is not None:
            raise ResourceInactive(message=f'{inactive.name} is not available for booking')

        office_id = room.office_id if room is not None else equipment[0].office_id
        if any(item.office_id != office_id for item in equipment):
            raise ResourceOfficeMismatch

        fixed_elsewhere = next(
            (item for item in equipment if not item.is_available_in_room(draft.room_id)),
            None,
        )
        if fixed_elsewhere is not None:
            raise EquipmentNotMovable(
                message=f'{fixed_elsewhere.name} is installed in another room and cannot be moved'
            )

        return await self._require_office(office_id), room, equipment

    @staticmethod
    def _build_recurrence(office: Office, draft: BookingDraft) -> Recurrence | None:
        if draft.recurrence is None:
            return None

        return Recurrence(
            office,
            draft.recurrence.frequency,
            interval=draft.recurrence.interval,
            byweekday=draft.recurrence.byweekday,
            until=draft.recurrence.until,
            count=draft.recurrence.count,
        )

    async def _assert_free(
        self,
        room: Room | None,
        equipment: list[Equipment],
        windows: list[Window],
        *,
        exclude_booking_ids: list[UUID] | None = None,
    ) -> None:
        equipment_ids = [item.identifier for item in equipment]
        names = {item.identifier: item.name for item in equipment}

        for starts_at, ends_at in windows:
            if room is not None:
                conflicts = await self._bookings.find_room_conflicts(
                    room.identifier,
                    starts_at,
                    ends_at,
                    exclude_booking_ids=exclude_booking_ids,
                )
                if conflicts:
                    raise BookingConflict(message=f'{room.name} is already booked at {starts_at:%d.%m %H:%M} UTC')

            if equipment_ids:
                busy = await self._booking_equipment.find_conflicts(
                    equipment_ids,
                    starts_at,
                    ends_at,
                    exclude_booking_ids=exclude_booking_ids,
                )
                if busy:
                    name = names.get(busy[0].equipment_id, 'Equipment')
                    raise BookingConflict(message=f'{name} is already booked at {starts_at:%d.%m %H:%M} UTC')

    # --------- PARTICIPANTS ---------
    async def _resolve_participants(
        self,
        organizer: User,
        draft: BookingDraft,
        office: Office,
    ) -> dict[str, UUID | None]:
        """
        Map every attendee to an email and, where possible, to an account.

        The organizer always comes first so that ``_insert`` can mark them as the organizer.
        Unknown addresses get an ``invited`` placeholder account: the person is a real attendee
        of a real booking, and a row now is what lets them see it the moment they register.
        """
        resolved: dict[str, UUID | None] = {organizer.email: organizer.identifier}

        if draft.participant_user_ids:
            users = await self._users.get_by_ids(draft.participant_user_ids)
            if len(users) != len(set(draft.participant_user_ids)):
                raise NotFound(message='Some of the selected users do not exist')

            for user in users:
                resolved.setdefault(user.email, user.identifier)

        requested = [str(email).strip().lower() for email in draft.participant_emails]
        unknown = [email for email in requested if email not in resolved]
        if not unknown:
            return resolved

        known = {user.email: user for user in await self._users.get_by_emails(unknown)}
        for email in unknown:
            if email in resolved:
                continue

            user = known.get(email)
            if user is None:
                user = await self._users.create(
                    User(
                        email=email,
                        status=UserStatus.invited,
                        office_id=office.identifier,
                    )
                )
                await logger.ainfo('Created an invited placeholder account', email=email)

            resolved[email] = user.identifier

        return resolved

    async def _notify_invited(
        self,
        organizer: User,
        participants: dict[str, UUID | None],
    ) -> None:
        """Send account setup instructions without creating a second meeting invitation."""
        user_ids = [user_id for user_id in participants.values() if user_id is not None]
        users = await self._users.get_by_ids(user_ids)
        invited = [user for user in users if user.status is UserStatus.invited]
        if not invited:
            return

        for user in invited:
            try:
                await self._email.send_registration_invitation_email(
                    user_email=user.email,
                    organizer_name=organizer.display_name,
                    registration_url=(
                        f'{config.PUBLIC_BASE_URL.rstrip("/")}/register.html?{urlencode({"email": user.email})}'
                    ),
                )
            except Exception as exc:
                await logger.awarning(
                    'Could not send a registration invitation email', email=user.email, error=str(exc)
                )

    # --------- CALENDAR ---------
    async def _publish_to_calendar(  # noqa: PLR0913
        self,
        *,
        organizer: User,
        office: Office,
        room: Room | None,
        equipment: list[Equipment],
        booking: Booking,
        attendee_emails: list[str],
        rrule: str | None,
    ) -> str | None:
        draft = self._event_draft(
            office=office,
            room=room,
            equipment=equipment,
            booking=booking,
            attendee_emails=attendee_emails,
            organizer_email=organizer.email,
            rrule=rrule,
        )

        return await self._calendar.create_event(organizer.identifier, draft)

    async def _update_calendar(
        self,
        user: User,
        office: Office,
        room: Room | None,
        equipment: list[Equipment],
        booking: Booking,
    ) -> None:
        if booking.google_event_id is None:
            return

        participants = await self._participants.list_for_bookings([booking.identifier])
        draft = self._event_draft(
            office=office,
            room=room,
            equipment=equipment,
            booking=booking,
            attendee_emails=[participant.email for participant in participants],
            organizer_email=user.email,
            rrule=None,
        )

        await self._calendar.update_event(booking.organizer_id, booking.google_event_id, draft)

    async def _withdraw_from_calendar(self, user: User, booking: Booking, *, whole_series: bool) -> None:
        if booking.google_event_id is None:
            return

        del user  # Cancellation always acts on the organizer's calendar, even for an admin.

        if booking.series_id is not None and not whole_series:
            await self._calendar.cancel_occurrence(
                booking.organizer_id,
                booking.google_event_id,
                booking.starts_at,
                booking.ends_at,
            )
            return

        await self._calendar.delete_event(booking.organizer_id, booking.google_event_id)

    @staticmethod
    def _event_draft(  # noqa: PLR0913
        *,
        office: Office,
        room: Room | None,
        equipment: list[Equipment],
        booking: Booking,
        attendee_emails: list[str],
        organizer_email: str,
        rrule: str | None,
    ) -> CalendarEventDraft:
        location = f'{room.name}, {office.name}' if room else office.name

        description = booking.description or ''
        if equipment:
            listed = ', '.join(item.name for item in equipment)
            description = f'{description}\n\nEquipment: {listed}'.strip()

        base_url = config.PUBLIC_BASE_URL.rstrip('/')
        links = '\n'.join((f'Встречи в Slotify: {base_url}/my-bookings.html',))
        description = f'{description}\n\n{links}'.strip()

        return CalendarEventDraft(
            event_id=(booking.series_id or booking.identifier).hex,
            title=booking.title,
            description=description or None,
            location=location,
            starts_at=booking.starts_at,
            ends_at=booking.ends_at,
            timezone=office.timezone,
            attendee_emails=attendee_emails,
            organizer_email=organizer_email,
            recurrence=rrule,
        )

    # --------- LOOKUPS ---------
    async def _require_office(self, office_id: UUID) -> Office:
        office = await self._offices.get_by_id(office_id)
        if office is None:
            raise NotFound(message='Office not found')

        if not office.is_active:
            raise ResourceInactive(message=f'Office {office.name} is not accepting bookings')

        return office

    async def _require_booking(self, booking_id: UUID) -> Booking:
        booking = await self._bookings.get_by_id(booking_id)
        if booking is None:
            raise NotFound(message='Booking not found')

        return booking

    @staticmethod
    def default_range() -> tuple[datetime, datetime]:
        """The window "my bookings" shows by default: from now to a month ahead."""
        now = datetime.now(UTC)
        return now, now + timedelta(days=30)

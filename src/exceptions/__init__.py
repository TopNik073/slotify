import logging


class BaseServerError(Exception):
    level = logging.NOTSET
    http_code: int
    message: str | None
    code: str | None

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        level: int | None = None,
        http_code: int | None = None,
    ):
        super().__init__(message)
        self.message = message or self.message
        self.code = code or self.code
        self.level = level or self.level
        self.http_code = http_code or self.http_code


class ServerError(BaseServerError):
    level = logging.ERROR
    http_code = 500


class ClientError(BaseServerError):
    level = logging.WARNING
    http_code = 400


class NotFound(ClientError):
    http_code = 404
    code = 'not_found'
    message = 'The requested resource is not found'


class PermissionDenied(ClientError):
    http_code = 403
    code = 'permission_denied'
    message = 'Insufficient permissions'


class Conflict(ClientError):
    http_code = 409
    code = 'conflict'
    message = 'The conflict was occurred while processing the request'


class RedisException(ClientError):
    level = logging.ERROR
    http_code = 500
    code = 'redis_exception'
    message = 'Redis server error'


# --------- AUTH ---------
class EmailAlreadyExists(ClientError):
    code = 'email_exists'
    message = 'User with this email already exists'
    http_code = 409


class InvalidCredentials(ClientError):
    code = 'invalid_credentials'
    message = 'Invalid email or password'


class SessionExpired(ClientError):
    code = 'session_expired'
    message = 'Session expired or not found'


class InvalidSessionData(ClientError):
    code = 'invalid_session_data'
    message = 'Invalid session data'


class InvalidCode(ClientError):
    code = 'invalid_code'
    message = 'Invalid verification code'


class CodeExpired(ClientError):
    code = 'code_expired'
    message = 'Code expired'


class InvalidSessionType(ClientError):
    code = 'invalid_session_type'
    message = 'Invalid session type'


class InvalidToken(ClientError):
    http_code = 401
    code = 'invalid_token'
    message = 'Invalid or expired token'


class AccountDisabled(ClientError):
    http_code = 403
    code = 'account_disabled'
    message = 'This account is disabled'


class PasswordLoginUnavailable(ClientError):
    code = 'password_login_unavailable'
    message = 'This account has no password set, sign in with Google instead'


# --------- BOOKING ---------
class BookingConflict(Conflict):
    code = 'booking_conflict'
    message = 'The room or equipment is already booked for this time'


class InvalidBookingWindow(ClientError):
    code = 'invalid_booking_window'
    message = 'Booking must end after it starts'


class BookingInPast(ClientError):
    code = 'booking_in_past'
    message = 'Cannot book a time that has already passed'


class BookingTooFarAhead(ClientError):
    code = 'booking_too_far_ahead'
    message = 'Booking is beyond the horizon allowed by this office'


class SlotNotAligned(ClientError):
    code = 'slot_not_aligned'
    message = 'Booking must start and end on the office slot grid'


class BookingDurationNotAllowed(ClientError):
    code = 'booking_duration_not_allowed'
    message = 'Booking duration is outside the limits of this office'


class OutsideWorkingHours(ClientError):
    code = 'outside_working_hours'
    message = 'The office is closed at this time'


class NothingToBook(ClientError):
    code = 'nothing_to_book'
    message = 'A booking must include a room or at least one piece of equipment'


class ResourceInactive(ClientError):
    code = 'resource_inactive'
    message = 'This room or equipment is no longer available for booking'


class ResourceOfficeMismatch(ClientError):
    code = 'resource_office_mismatch'
    message = 'Room and equipment must belong to the same office'


class EquipmentNotMovable(ClientError):
    code = 'equipment_not_movable'
    message = 'This equipment is fixed to another room and cannot be moved'


class RecurrenceNotAllowed(ClientError):
    code = 'recurrence_not_allowed'
    message = 'Recurrence rule produces no occurrences or too many of them'


# --------- GOOGLE ---------
class GoogleAuthFailed(ClientError):
    code = 'google_auth_failed'
    message = 'Google sign-in failed'


class GoogleStateMismatch(ClientError):
    code = 'google_state_mismatch'
    message = 'Google sign-in state is missing or expired, start again'


class GoogleCalendarNotConnected(ClientError):
    code = 'google_calendar_not_connected'
    message = 'Connect your Google calendar to sync bookings'


class GoogleApiError(ServerError):
    code = 'google_api_error'
    message = 'Google API request failed'

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ):
        super().__init__(message, code=code)
        # The status Google replied with, so callers can tell "already deleted" from a real failure.
        self.status_code = status_code

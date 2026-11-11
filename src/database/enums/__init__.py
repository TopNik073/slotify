from enum import StrEnum


class UserRole(StrEnum):
    user = 'user'
    admin = 'admin'


class UserStatus(StrEnum):
    """
    ``invited`` is a placeholder account created when a booking organizer adds a participant
    by email that is not registered yet. It has no password and cannot log in until the person
    completes registration (or signs in with Google using the same email).
    """

    active = 'active'
    invited = 'invited'
    disabled = 'disabled'


class EquipmentType(StrEnum):
    projector = 'projector'
    tv = 'tv'
    whiteboard = 'whiteboard'
    conference_phone = 'conference_phone'
    video_camera = 'video_camera'
    microphone = 'microphone'
    laptop = 'laptop'
    other = 'other'


class BookingStatus(StrEnum):
    active = 'active'
    cancelled = 'cancelled'


class ParticipantResponse(StrEnum):
    """Mirrors the ``responseStatus`` values of a Google Calendar attendee."""

    needs_action = 'needs_action'
    accepted = 'accepted'
    declined = 'declined'
    tentative = 'tentative'


class RecurrenceFrequency(StrEnum):
    daily = 'daily'
    weekly = 'weekly'


__all__ = [
    'BookingStatus',
    'EquipmentType',
    'ParticipantResponse',
    'RecurrenceFrequency',
    'UserRole',
    'UserStatus',
]

"""Initial schema

Revision ID: 0000_2026_10_14_09_36
Revises: 
Create Date: 2026-10-14 11:36:02.595311

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


USER_ROLE = postgresql.ENUM('user', 'admin', name='user_role', create_type=False)
USER_STATUS = postgresql.ENUM('active', 'invited', 'disabled', name='user_status', create_type=False)
EQUIPMENT_TYPE = postgresql.ENUM(
    'projector',
    'tv',
    'whiteboard',
    'conference_phone',
    'video_camera',
    'microphone',
    'laptop',
    'other',
    name='equipment_type',
    create_type=False,
)
BOOKING_STATUS = postgresql.ENUM('active', 'cancelled', name='booking_status', create_type=False)
PARTICIPANT_RESPONSE = postgresql.ENUM(
    'needs_action',
    'accepted',
    'declined',
    'tentative',
    name='participant_response',
    create_type=False,
)
RECURRENCE_FREQUENCY = postgresql.ENUM('daily', 'weekly', name='recurrence_frequency', create_type=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    # Required for an exclusion constraint that mixes equality on a uuid with range overlap.
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')

    op.execute("CREATE TYPE user_role AS ENUM ('user', 'admin')")
    op.execute("CREATE TYPE user_status AS ENUM ('active', 'invited', 'disabled')")
    op.execute(
        "CREATE TYPE equipment_type AS ENUM ('projector', 'tv', 'whiteboard', 'conference_phone', "
        "'video_camera', 'microphone', 'laptop', 'other')"
    )
    op.execute("CREATE TYPE booking_status AS ENUM ('active', 'cancelled')")
    op.execute("CREATE TYPE participant_response AS ENUM ('needs_action', 'accepted', 'declined', 'tentative')")
    op.execute("CREATE TYPE recurrence_frequency AS ENUM ('daily', 'weekly')")

    op.create_table(
        'offices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('city', sa.String(255), nullable=False),
        sa.Column('address', sa.String(512), nullable=True),
        sa.Column('timezone', sa.String(64), nullable=False),
        sa.Column('workdays', postgresql.ARRAY(sa.SmallInteger()), nullable=False),
        sa.Column('opens_at', sa.Time(), nullable=False),
        sa.Column('closes_at', sa.Time(), nullable=False),
        sa.Column('slot_minutes', sa.Integer(), nullable=False),
        sa.Column('min_booking_minutes', sa.Integer(), nullable=False),
        sa.Column('max_booking_minutes', sa.Integer(), nullable=False),
        sa.Column('booking_horizon_days', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('role', USER_ROLE, nullable=False),
        sa.Column('status', USER_STATUS, nullable=False),
        sa.Column(
            'office_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('offices.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('google_sub', sa.String(255), nullable=True, unique=True),
        sa.Column('avatar_url', sa.String(1024), nullable=True),
        *_timestamps(),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_office_id', 'users', ['office_id'])

    op.create_table(
        'google_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
        ),
        sa.Column('google_sub', sa.String(255), nullable=False, unique=True),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scopes', postgresql.ARRAY(sa.String(255)), nullable=False),
        sa.Column('calendar_connected', sa.Boolean(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        'rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'office_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('offices.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('floor', sa.String(32), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint('office_id', 'name', name='rooms_office_name_unique'),
    )
    op.create_index('ix_rooms_office_id', 'rooms', ['office_id'])

    op.create_table(
        'equipment',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'office_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('offices.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', EQUIPMENT_TYPE, nullable=False),
        sa.Column('inventory_number', sa.String(64), nullable=True, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'home_room_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('rooms.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('is_movable', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index('ix_equipment_office_id', 'equipment', ['office_id'])
    op.create_index('ix_equipment_home_room_id', 'equipment', ['home_room_id'])

    op.create_table(
        'booking_series',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'organizer_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('frequency', RECURRENCE_FREQUENCY, nullable=False),
        sa.Column('interval', sa.Integer(), nullable=False),
        sa.Column('byweekday', postgresql.ARRAY(sa.SmallInteger()), nullable=True),
        sa.Column('until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=True),
        sa.Column('rrule', sa.Text(), nullable=False),
        sa.Column('google_event_id', sa.String(1024), nullable=True),
        sa.Column('google_calendar_id', sa.String(320), nullable=True),
        *_timestamps(),
    )
    op.create_index('ix_booking_series_organizer_id', 'booking_series', ['organizer_id'])

    op.create_table(
        'bookings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'organizer_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'office_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('offices.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'room_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('rooms.id', ondelete='CASCADE'),
            nullable=True,
        ),
        sa.Column(
            'series_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('booking_series.id', ondelete='CASCADE'),
            nullable=True,
        ),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', BOOKING_STATUS, nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('google_event_id', sa.String(1024), nullable=True),
        sa.Column('google_calendar_id', sa.String(320), nullable=True),
        *_timestamps(),
        sa.CheckConstraint('ends_at > starts_at', name='bookings_end_after_start'),
    )
    op.create_index('ix_bookings_organizer_id', 'bookings', ['organizer_id'])
    op.create_index('ix_bookings_office_id', 'bookings', ['office_id'])
    op.create_index('ix_bookings_room_id', 'bookings', ['room_id'])
    op.create_index('ix_bookings_series_id', 'bookings', ['series_id'])
    op.create_index('ix_bookings_starts_at', 'bookings', ['starts_at'])
    op.create_index('ix_bookings_ends_at', 'bookings', ['ends_at'])

    # Two active bookings of the same room may not overlap. Touching edges are fine because
    # tstzrange is half-open: [10:00, 11:00) and [11:00, 12:00) do not intersect.
    op.execute(
        """
        ALTER TABLE bookings
        ADD CONSTRAINT bookings_room_no_overlap
        EXCLUDE USING gist (
            room_id WITH =,
            tstzrange(starts_at, ends_at) WITH &&
        )
        WHERE (status = 'active' AND room_id IS NOT NULL)
        """
    )

    op.create_table(
        'booking_equipment',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'booking_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('bookings.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'equipment_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('equipment.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', BOOKING_STATUS, nullable=False),
        sa.UniqueConstraint('booking_id', 'equipment_id', name='booking_equipment_unique'),
    )
    op.create_index('ix_booking_equipment_booking_id', 'booking_equipment', ['booking_id'])
    op.create_index('ix_booking_equipment_equipment_id', 'booking_equipment', ['equipment_id'])

    # Same guarantee as above, per unit of equipment. The time window is duplicated from the
    # parent booking because an exclusion constraint cannot read another table.
    op.execute(
        """
        ALTER TABLE booking_equipment
        ADD CONSTRAINT booking_equipment_no_overlap
        EXCLUDE USING gist (
            equipment_id WITH =,
            tstzrange(starts_at, ends_at) WITH &&
        )
        WHERE (status = 'active')
        """
    )

    op.create_table(
        'booking_participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'booking_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('bookings.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('is_organizer', sa.Boolean(), nullable=False),
        sa.Column('response', PARTICIPANT_RESPONSE, nullable=False),
        *_timestamps(),
        sa.UniqueConstraint('booking_id', 'email', name='booking_participants_unique'),
    )
    op.create_index('ix_booking_participants_booking_id', 'booking_participants', ['booking_id'])
    op.create_index('ix_booking_participants_user_id', 'booking_participants', ['user_id'])


def downgrade() -> None:
    op.drop_table('booking_participants')
    op.drop_table('booking_equipment')
    op.drop_table('bookings')
    op.drop_table('booking_series')
    op.drop_table('equipment')
    op.drop_table('rooms')
    op.drop_table('google_accounts')
    op.drop_table('users')
    op.drop_table('offices')

    op.execute('DROP TYPE IF EXISTS recurrence_frequency')
    op.execute('DROP TYPE IF EXISTS participant_response')
    op.execute('DROP TYPE IF EXISTS booking_status')
    op.execute('DROP TYPE IF EXISTS equipment_type')
    op.execute('DROP TYPE IF EXISTS user_status')
    op.execute('DROP TYPE IF EXISTS user_role')

"""
Fill an empty database with one office, a few rooms and some equipment.

Useful right after the first migration, so the booking page has something to show:

    uv run python -m src.scripts.seed_demo
"""

import asyncio

from datetime import time

from src.core.config import config
from src.database.connection import AsyncSessionLocal
from src.database.enums import EquipmentType
from src.database.repository import Equipment
from src.database.repository import EquipmentRepository
from src.database.repository import Office
from src.database.repository import OfficeRepository
from src.database.repository import Room
from src.database.repository import RoomRepository

OFFICE_NAME = 'Главный офис'

ROOMS = [
    # name, capacity, floor, fixed equipment installed in this room
    ('Невский', 12, '3', [('Проектор Epson', EquipmentType.projector), ('Доска', EquipmentType.whiteboard)]),
    ('Фонтанка', 6, '3', [('Телевизор LG', EquipmentType.tv)]),
    ('Мойка', 4, '2', []),
]

MOVABLE_EQUIPMENT = [
    ('Камера Logitech', EquipmentType.video_camera),
    ('Микрофон Shure', EquipmentType.microphone),
    ('Ноутбук для презентаций', EquipmentType.laptop),
]


async def seed() -> str:
    async with AsyncSessionLocal() as session:
        offices = OfficeRepository(session)
        rooms = RoomRepository(session)
        equipment = EquipmentRepository(session)

        if await offices.get_by_name(OFFICE_NAME) is not None:
            return 'Demo data already present, nothing to do'

        office = await offices.create(
            Office(
                name=OFFICE_NAME,
                city='Санкт-Петербург',
                timezone='Europe/Moscow',
                workdays=[1, 2, 3, 4, 5],
                opens_at=time(9, 0),
                closes_at=time(20, 0),
            )
        )

        created_rooms = 0
        created_equipment = 0

        for name, capacity, floor, fixtures in ROOMS:
            room = await rooms.create(Room(office_id=office.identifier, name=name, capacity=capacity, floor=floor))
            created_rooms += 1

            for item_name, item_type in fixtures:
                await equipment.create(
                    Equipment(
                        office_id=office.identifier,
                        name=f'{item_name} ({name})',
                        type=item_type,
                        home_room_id=room.identifier,
                        is_movable=False,
                    )
                )
                created_equipment += 1

        for item_name, item_type in MOVABLE_EQUIPMENT:
            await equipment.create(
                Equipment(office_id=office.identifier, name=item_name, type=item_type, is_movable=True)
            )
            created_equipment += 1

        await session.commit()

        return f'Created office "{OFFICE_NAME}", {created_rooms} rooms, {created_equipment} equipment units'


if __name__ == '__main__':
    import sys

    try:
        print(asyncio.run(seed()))  # noqa: T201
    except OSError as exc:
        sys.exit(f'Cannot reach the database at {config.DB_HOST}:{config.DB_PORT} ({exc})')

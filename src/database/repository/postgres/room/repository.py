from uuid import UUID

from sqlalchemy import select

from src.database.models import RoomORM
from src.database.repository.postgres.base import BasePostgresRepository
from src.database.repository.postgres.base import orm_kwargs
from src.database.repository.postgres.room.dtos import Room


class RoomRepository(BasePostgresRepository[RoomORM, Room]):
    _orm_class = RoomORM

    def orm_to_model(self, orm: RoomORM) -> Room:
        return Room.model_validate(orm)

    def model_to_orm(self, model: Room) -> RoomORM:
        return RoomORM(**orm_kwargs(model))

    async def get_by_ids(self, room_ids: list[UUID]) -> list[Room]:
        if not room_ids:
            return []

        stmt = select(RoomORM).where(RoomORM.id.in_(room_ids))
        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def get_by_office_and_name(self, office_id: UUID, name: str) -> Room | None:
        stmt = select(RoomORM).where(RoomORM.office_id == office_id, RoomORM.name == name)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self.orm_to_model(orm) if orm else None

    async def list_rooms(
        self,
        *,
        office_id: UUID | None = None,
        min_capacity: int | None = None,
        only_active: bool = True,
        limit: int | None = None,
    ) -> list[Room]:
        stmt = select(RoomORM).order_by(RoomORM.name)
        if office_id is not None:
            stmt = stmt.where(RoomORM.office_id == office_id)
        if min_capacity is not None:
            stmt = stmt.where(RoomORM.capacity >= min_capacity)
        if only_active:
            stmt = stmt.where(RoomORM.is_active.is_(True))
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

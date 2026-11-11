from uuid import UUID

from sqlalchemy import or_
from sqlalchemy import select

from src.database.enums import EquipmentType
from src.database.models import EquipmentORM
from src.database.repository.postgres.base import BasePostgresRepository
from src.database.repository.postgres.base import orm_kwargs
from src.database.repository.postgres.equipment.dtos import Equipment


class EquipmentRepository(BasePostgresRepository[EquipmentORM, Equipment]):
    _orm_class = EquipmentORM

    def orm_to_model(self, orm: EquipmentORM) -> Equipment:
        return Equipment.model_validate(orm)

    def model_to_orm(self, model: Equipment) -> EquipmentORM:
        return EquipmentORM(**orm_kwargs(model))

    async def get_by_ids(self, equipment_ids: list[UUID]) -> list[Equipment]:
        if not equipment_ids:
            return []

        stmt = select(EquipmentORM).where(EquipmentORM.id.in_(equipment_ids))
        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def get_by_inventory_number(self, inventory_number: str) -> Equipment | None:
        stmt = select(EquipmentORM).where(EquipmentORM.inventory_number == inventory_number)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self.orm_to_model(orm) if orm else None

    async def list_equipment(
        self,
        *,
        office_id: UUID | None = None,
        types: list[EquipmentType] | None = None,
        room_id: UUID | None = None,
        only_active: bool = True,
        limit: int | None = None,
    ) -> list[Equipment]:
        """
        ``room_id`` returns everything usable in that room: the units installed there plus every
        movable unit of the office, which is exactly the choice an organizer has when booking it.
        """
        stmt = select(EquipmentORM).order_by(EquipmentORM.type, EquipmentORM.name)
        if office_id is not None:
            stmt = stmt.where(EquipmentORM.office_id == office_id)
        if types:
            stmt = stmt.where(EquipmentORM.type.in_(types))
        if room_id is not None:
            stmt = stmt.where(
                or_(
                    EquipmentORM.home_room_id == room_id,
                    EquipmentORM.is_movable.is_(True),
                )
            )
        if only_active:
            stmt = stmt.where(EquipmentORM.is_active.is_(True))
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

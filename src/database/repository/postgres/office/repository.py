from sqlalchemy import select

from src.database.models import OfficeORM
from src.database.repository.postgres.base import BasePostgresRepository
from src.database.repository.postgres.base import orm_kwargs
from src.database.repository.postgres.office.dtos import Office


class OfficeRepository(BasePostgresRepository[OfficeORM, Office]):
    _orm_class = OfficeORM

    def orm_to_model(self, orm: OfficeORM) -> Office:
        return Office.model_validate(orm)

    def model_to_orm(self, model: Office) -> OfficeORM:
        return OfficeORM(**orm_kwargs(model))

    async def get_by_name(self, name: str) -> Office | None:
        stmt = select(OfficeORM).where(OfficeORM.name == name)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self.orm_to_model(orm) if orm else None

    async def get_many(self, limit: int | None = None, *, only_active: bool = False) -> list[Office]:
        stmt = select(OfficeORM).order_by(OfficeORM.city, OfficeORM.name)
        if only_active:
            stmt = stmt.where(OfficeORM.is_active.is_(True))
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

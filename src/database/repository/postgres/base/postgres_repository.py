from abc import ABC
from abc import abstractmethod
from typing import Annotated
from typing import TypeVar
from uuid import UUID

from fastapi.params import Depends
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.models.base import BaseORM
from src.database.repository.base.models import BaseModelIdentifiable
from src.database.repository.base.repository import BaseRepository
from src.database.repository.postgres.errors import BasePostgresError

ORMType = TypeVar('ORMType', bound=BaseORM)
ModelType = TypeVar('ModelType', bound=BaseModelIdentifiable)

_DB_GENERATED_FIELDS = ('id', 'created_at', 'updated_at')


def orm_kwargs(model: BaseModelIdentifiable) -> dict[str, object]:
    """
    Dump a model into ORM constructor kwargs.

    Only the database-generated fields are dropped when unset, so that ``id`` and the timestamps
    fall back to their column defaults. Every other ``None`` is kept on purpose: it is how a
    nullable field gets cleared through ``update()``.
    """
    data = model.model_dump()
    for field in _DB_GENERATED_FIELDS:
        if data.get(field) is None:
            data.pop(field, None)

    return data


class BasePostgresRepository(
    BaseRepository[ORMType, ModelType],
    ABC,
):
    _orm_class: type[ORMType]

    def __init__(
        self,
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> None:
        self._session = session

    @abstractmethod
    def orm_to_model(self, orm: ORMType) -> ModelType:
        raise NotImplementedError

    @abstractmethod
    def model_to_orm(self, model: ModelType) -> ORMType:
        raise NotImplementedError

    async def get_by_id(self, _id: UUID) -> ModelType | None:
        orm = await self._session.get(self._orm_class, _id)
        if orm is None:
            return None
        return self.orm_to_model(orm)

    async def get_many(self, limit: int | None = None) -> list[ModelType]:
        stmt = select(self._orm_class)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all() if orm is not None]

    async def create(self, entity: ModelType) -> ModelType:
        """
        Persist a new entity within the caller's transaction.

        Writes flush rather than commit: the transaction boundary is the request, closed by
        ``get_session``. A commit here would make every repository call its own transaction, so a
        booking could be committed and then its equipment rows rejected, leaving a booking that
        reserves nothing.
        """
        orm = self.model_to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return self.orm_to_model(orm)

    async def update(self, entity: ModelType) -> ModelType:
        orm = await self._session.get(self._orm_class, entity.id)

        if orm is None:
            msg: str = f'Entity with id {entity.id} not found'
            raise BasePostgresError(msg)

        updated_orm = self.model_to_orm(entity)
        data = updated_orm.__dict__.copy()
        data.pop('id', None)
        data.pop('_sa_instance_state', None)

        for field, value in data.items():
            if not field.startswith('_'):
                setattr(orm, field, value)

        await self._session.flush()
        await self._session.refresh(orm)

        return self.orm_to_model(orm)

    async def delete(self, _id: UUID) -> bool:
        query = delete(self._orm_class).where(self._orm_class.id == _id)
        result = await self._session.execute(query)
        await self._session.flush()
        return result.rowcount > 0

from uuid import UUID

from sqlalchemy import select

from src.database.models import GoogleAccountORM
from src.database.repository.postgres.base import BasePostgresRepository
from src.database.repository.postgres.base import orm_kwargs
from src.database.repository.postgres.google_account.dtos import GoogleAccount


class GoogleAccountRepository(BasePostgresRepository[GoogleAccountORM, GoogleAccount]):
    _orm_class = GoogleAccountORM

    def orm_to_model(self, orm: GoogleAccountORM) -> GoogleAccount:
        return GoogleAccount.model_validate(orm)

    def model_to_orm(self, model: GoogleAccount) -> GoogleAccountORM:
        return GoogleAccountORM(**orm_kwargs(model))

    async def get_by_user_id(self, user_id: UUID) -> GoogleAccount | None:
        stmt = select(GoogleAccountORM).where(GoogleAccountORM.user_id == user_id)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self.orm_to_model(orm) if orm else None

    async def get_by_google_sub(self, google_sub: str) -> GoogleAccount | None:
        stmt = select(GoogleAccountORM).where(GoogleAccountORM.google_sub == google_sub)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self.orm_to_model(orm) if orm else None

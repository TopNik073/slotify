from uuid import UUID

from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select

from src.database.enums import UserRole
from src.database.enums import UserStatus
from src.database.models import UserORM
from src.database.repository.postgres.base import BasePostgresRepository
from src.database.repository.postgres.base import orm_kwargs
from src.database.repository.postgres.user.dtos import User


class UserRepository(BasePostgresRepository[UserORM, User]):
    _orm_class = UserORM

    def orm_to_model(self, orm: UserORM) -> User:
        return User.model_validate(orm)

    def model_to_orm(self, model: User) -> UserORM:
        return UserORM(**orm_kwargs(model))

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserORM).where(UserORM.email == email.lower())
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self.orm_to_model(orm) if orm else None

    async def get_by_google_sub(self, google_sub: str) -> User | None:
        stmt = select(UserORM).where(UserORM.google_sub == google_sub)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self.orm_to_model(orm) if orm else None

    async def get_by_ids(self, user_ids: list[UUID]) -> list[User]:
        if not user_ids:
            return []

        stmt = select(UserORM).where(UserORM.id.in_(user_ids))
        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def get_by_emails(self, emails: list[str]) -> list[User]:
        if not emails:
            return []

        stmt = select(UserORM).where(UserORM.email.in_([email.lower() for email in emails]))
        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def list_users(  # noqa: PLR0913
        self,
        *,
        office_id: UUID | None = None,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """Filtered listing for the admin panel."""
        stmt = (
            select(UserORM)
            .where(*self._list_filters(office_id, role, status, query))
            .order_by(UserORM.created_at.desc(), UserORM.id.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

    async def count_users(
        self,
        *,
        office_id: UUID | None = None,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        query: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(UserORM).where(*self._list_filters(office_id, role, status, query))
        return (await self._session.execute(stmt)).scalar_one()

    @staticmethod
    def _list_filters(office_id, role, status, query):
        filters = []
        if office_id is not None:
            filters.append(UserORM.office_id == office_id)
        if role is not None:
            filters.append(UserORM.role == role)
        if status is not None:
            filters.append(UserORM.status == status)
        if query and query.strip():
            escaped = query.strip().replace('\\', '\\\\').replace('%', r'\%').replace('_', r'\_')
            pattern = f'%{escaped}%'
            filters.append(
                or_(UserORM.email.ilike(pattern, escape='\\'), UserORM.full_name.ilike(pattern, escape='\\'))
            )
        return filters

    async def search(
        self,
        query: str,
        *,
        office_id: UUID | None = None,
        limit: int = 20,
    ) -> list[User]:
        """Directory lookup used when an organizer picks participants for a booking."""
        pattern = f'%{query.strip().lower()}%'
        stmt = (
            select(UserORM)
            .where(
                UserORM.status != UserStatus.disabled,
                or_(UserORM.email.ilike(pattern), UserORM.full_name.ilike(pattern)),
            )
            .order_by(UserORM.full_name.nulls_last(), UserORM.email)
            .limit(limit)
        )
        if office_id is not None:
            stmt = stmt.where(UserORM.office_id == office_id)

        result = await self._session.execute(stmt)
        return [self.orm_to_model(orm) for orm in result.scalars().all()]

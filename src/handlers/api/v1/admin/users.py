from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from src.database.enums import UserRole
from src.database.enums import UserStatus
from src.database.repository import OfficeRepository
from src.database.repository import User
from src.database.repository import UserRepository
from src.exceptions import ClientError
from src.exceptions import NotFound
from src.handlers.api.v1.admin.models import UserUpdateRequest
from src.handlers.api.v1.users.models import AdminUserListResponse
from src.handlers.api.v1.users.models import UserResponse
from src.handlers.dependencies.auth import get_current_admin

admin_users_router = APIRouter(prefix='/users', tags=['admin: users'])


@admin_users_router.get('/', response_model=AdminUserListResponse)
async def list_users(  # noqa: PLR0913, PLR0917
    users: Annotated[UserRepository, Depends()],
    office_id: Annotated[UUID | None, Query(alias='officeId')] = None,
    role: Annotated[UserRole | None, Query()] = None,
    status: Annotated[UserStatus | None, Query()] = None,
    query: Annotated[str | None, Query(alias='q', max_length=320)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminUserListResponse:
    found = await users.list_users(
        office_id=office_id,
        role=role,
        status=status,
        query=query,
        limit=limit,
        offset=offset,
    )

    total = await users.count_users(office_id=office_id, role=role, status=status, query=query)
    return AdminUserListResponse(
        users=[UserResponse.model_validate(user) for user in found],
        total=total,
        limit=limit,
        offset=offset,
    )


@admin_users_router.patch('/{user_id}', response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    admin: Annotated[User, Depends(get_current_admin)],
    users: Annotated[UserRepository, Depends()],
    offices: Annotated[OfficeRepository, Depends()],
) -> UserResponse:
    """
    Change a user's role, status, office or name.

    An admin cannot demote or disable themselves: doing so by accident would leave the
    installation without anyone able to undo it.
    """
    user = await users.get_by_id(user_id)
    if user is None:
        raise NotFound(message='User not found')

    changes = payload.model_dump(exclude_unset=True)

    if user_id == admin.identifier:
        if changes.get('role') is not None and changes['role'] is not UserRole.admin:
            raise ClientError(message='You cannot remove your own admin rights', code='self_demotion')

        if changes.get('status') is not None and changes['status'] is not UserStatus.active:
            raise ClientError(message='You cannot disable your own account', code='self_disable')

    if changes.get('office_id') is not None and await offices.get_by_id(changes['office_id']) is None:
        raise NotFound(message='Office not found')

    updated = await users.update(user.model_copy(update=changes))

    return UserResponse.model_validate(updated)


@admin_users_router.delete('/{user_id}', status_code=204)
async def delete_user(
    user_id: UUID,
    admin: Annotated[User, Depends(get_current_admin)],
    users: Annotated[UserRepository, Depends()],
) -> None:
    """Deletes the account and the bookings it organized; disabling is the softer option."""
    if user_id == admin.identifier:
        raise ClientError(message='You cannot delete your own account', code='self_deletion')

    if not await users.delete(user_id):
        raise NotFound(message='User not found')

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from src.database.repository import OfficeRepository
from src.database.repository import User
from src.database.repository import UserRepository
from src.exceptions import NotFound
from src.handlers.api.v1.users.models import CurrentUserResponse
from src.handlers.api.v1.users.models import UpdateProfileRequest
from src.handlers.api.v1.users.models import UserListResponse
from src.handlers.api.v1.users.models import UserResponse
from src.handlers.dependencies.auth import get_current_user
from src.services.google import CalendarService

users_router = APIRouter(prefix='/users', tags=['users'])


@users_router.get('/me', response_model=CurrentUserResponse)
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
    calendar: Annotated[CalendarService, Depends()],
) -> CurrentUserResponse:
    return CurrentUserResponse(
        **UserResponse.model_validate(user).model_dump(),
        google_calendar_connected=await calendar.is_connected(user.identifier),
    )


@users_router.patch('/me', response_model=CurrentUserResponse)
async def update_me(
    payload: UpdateProfileRequest,
    user: Annotated[User, Depends(get_current_user)],
    users: Annotated[UserRepository, Depends()],
    offices: Annotated[OfficeRepository, Depends()],
    calendar: Annotated[CalendarService, Depends()],
) -> CurrentUserResponse:
    if 'full_name' in payload.model_fields_set:
        user.full_name = payload.full_name

    if 'office_id' in payload.model_fields_set:
        if payload.office_id is not None and await offices.get_by_id(payload.office_id) is None:
            raise NotFound(message='Office not found')

        user.office_id = payload.office_id

    updated = await users.update(user)

    return CurrentUserResponse(
        **UserResponse.model_validate(updated).model_dump(),
        google_calendar_connected=await calendar.is_connected(updated.identifier),
    )


@users_router.get('/search', response_model=UserListResponse)
async def search_users(
    _: Annotated[User, Depends(get_current_user)],
    users: Annotated[UserRepository, Depends()],
    query: Annotated[str, Query(min_length=2, max_length=320, alias='q')],
    office_id: Annotated[UUID | None, Query(alias='officeId')] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> UserListResponse:
    """
    Directory lookup for picking participants.

    Invited placeholders are included on purpose: someone already invited by email should be
    found by name instead of being invited a second time as a duplicate address.
    """
    found = await users.search(query, office_id=office_id, limit=limit)

    return UserListResponse(users=[UserResponse.model_validate(item) for item in found])

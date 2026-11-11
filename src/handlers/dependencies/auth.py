from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

from src.database.enums import UserStatus
from src.database.repository.postgres.user.dtos import User
from src.exceptions import AccountDisabled
from src.exceptions import InvalidToken
from src.exceptions import PermissionDenied
from src.services.auth.service import AuthService

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    service: Annotated[AuthService, Depends(AuthService)],
) -> User:
    user, _, token_type = await service.verify_token(credentials.credentials)
    if token_type != 'access':
        raise InvalidToken

    if user.status is UserStatus.disabled:
        raise AccountDisabled

    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Guards everything under ``/api/v1/admin``."""
    if not user.is_admin:
        raise PermissionDenied(message='This operation requires administrator rights')

    return user

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends

from src.handlers.api.v1.auth.refresh.models import RefreshRequest
from src.handlers.api.v1.auth.refresh.models import RefreshResponse
from src.services.auth.service import AuthService

refresh_router = APIRouter(prefix='/refresh')


@refresh_router.post('/', response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest,
    service: Annotated[AuthService, Depends(AuthService)],
) -> RefreshResponse:
    tokens = await service.refresh_tokens(
        refresh_token=payload.refresh_token,
    )

    return RefreshResponse(accessToken=tokens.access.token, refreshToken=tokens.refresh.token)

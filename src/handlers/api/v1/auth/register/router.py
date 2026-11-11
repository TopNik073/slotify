from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends

from src.handlers.api.v1.auth.register.models import RegisterRequest
from src.handlers.api.v1.auth.register.models import RegisterResponse
from src.services.auth.service import AuthService

register_router = APIRouter(prefix='/register')


@register_router.post('/', response_model=RegisterResponse)
async def register(
    payload: RegisterRequest,
    service: Annotated[AuthService, Depends()],
) -> RegisterResponse:
    """
    Start registration by sending a confirmation code.

    The account appears only after the code is confirmed at ``/auth/2fa/register``.
    """
    await service.start_registration(
        email=str(payload.email),
        password=payload.password,
        full_name=payload.full_name,
        office_id=payload.office_id,
    )

    return RegisterResponse()

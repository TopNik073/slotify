from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from pydantic import ValidationError

from src.database.repository import Office
from src.database.repository import OfficeRepository
from src.exceptions import ClientError
from src.exceptions import Conflict
from src.exceptions import NotFound
from src.handlers.api.v1.admin.models import OfficeCreateRequest
from src.handlers.api.v1.admin.models import OfficeUpdateRequest
from src.handlers.api.v1.offices.models import OfficeResponse

admin_offices_router = APIRouter(prefix='/offices', tags=['admin: offices'])


def _as_office(payload: OfficeCreateRequest | Office) -> Office:
    """
    Build the domain model so its validators run before anything is written.

    The timezone and workday checks live on ``Office``, and a bad value has to come back as a
    400 with a readable message rather than as a validation error from deep inside the ORM.
    """
    try:
        # model_copy(update=...) does not validate changes; re-parse the data even when the
        # input is already an Office so PATCH cannot bypass timezone and workday validation.
        return Office.model_validate(payload.model_dump())
    except ValidationError as exc:
        raise ClientError(message=str(exc.errors()[0]['msg']), code='invalid_office') from exc


@admin_offices_router.post('/', response_model=OfficeResponse, status_code=201)
async def create_office(
    payload: OfficeCreateRequest,
    repository: Annotated[OfficeRepository, Depends()],
) -> OfficeResponse:
    if await repository.get_by_name(payload.name) is not None:
        raise Conflict(message='An office with this name already exists')

    created = await repository.create(_as_office(payload))

    return OfficeResponse.model_validate(created)


@admin_offices_router.patch('/{office_id}', response_model=OfficeResponse)
async def update_office(
    office_id: UUID,
    payload: OfficeUpdateRequest,
    repository: Annotated[OfficeRepository, Depends()],
) -> OfficeResponse:
    office = await repository.get_by_id(office_id)
    if office is None:
        raise NotFound(message='Office not found')

    changes = payload.model_dump(exclude_unset=True)
    if 'name' in changes:
        clash = await repository.get_by_name(changes['name'])
        if clash is not None and clash.identifier != office_id:
            raise Conflict(message='An office with this name already exists')

    updated = await repository.update(_as_office(office.model_copy(update=changes)))

    return OfficeResponse.model_validate(updated)


@admin_offices_router.delete('/{office_id}', status_code=204)
async def delete_office(
    office_id: UUID,
    repository: Annotated[OfficeRepository, Depends()],
) -> None:
    """
    Removes the office together with its rooms, equipment and bookings.

    Deactivating (``isActive: false``) is usually what is wanted instead: it stops new bookings
    while keeping the history.
    """
    if not await repository.delete(office_id):
        raise NotFound(message='Office not found')

from datetime import UTC
from datetime import datetime
from functools import lru_cache
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo
from zoneinfo import available_timezones

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from src.database.repository import OfficeRepository
from src.exceptions import NotFound
from src.handlers.api.v1.offices.models import OfficeListResponse
from src.handlers.api.v1.offices.models import OfficeResponse
from src.handlers.api.v1.offices.models import TimezoneListResponse
from src.handlers.api.v1.offices.models import TimezoneResponse

offices_router = APIRouter(prefix='/offices', tags=['offices'])


@offices_router.get('/', response_model=OfficeListResponse)
async def list_offices(
    repository: Annotated[OfficeRepository, Depends()],
    include_inactive: Annotated[bool, Query(alias='includeInactive')] = False,
) -> OfficeListResponse:
    """
    Offices available for booking and selecting a default office in the profile.
    """
    offices = await repository.get_many(only_active=not include_inactive)

    return OfficeListResponse(offices=[OfficeResponse.model_validate(office) for office in offices])


@lru_cache(maxsize=1)
def _timezone_names() -> tuple[str, ...]:
    return tuple(sorted(available_timezones() - {'localtime', 'posixrules'}))


@offices_router.get('/timezones', response_model=TimezoneListResponse)
async def list_timezones() -> TimezoneListResponse:
    now = datetime.now(UTC)
    entries = []
    for name in _timezone_names():
        offset = now.astimezone(ZoneInfo(name)).utcoffset()
        minutes = int(offset.total_seconds() // 60)
        sign = '+' if minutes >= 0 else '-'
        hours, remainder = divmod(abs(minutes), 60)
        entries.append(TimezoneResponse(id=name, utc_offset=f'UTC{sign}{hours:02d}:{remainder:02d}'))
    return TimezoneListResponse(timezones=entries)


@offices_router.get('/{office_id}', response_model=OfficeResponse)
async def get_office(
    office_id: UUID,
    repository: Annotated[OfficeRepository, Depends()],
) -> OfficeResponse:
    office = await repository.get_by_id(office_id)
    if office is None:
        raise NotFound(message='Office not found')

    return OfficeResponse.model_validate(office)

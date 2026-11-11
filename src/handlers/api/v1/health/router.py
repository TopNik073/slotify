from datetime import UTC
from datetime import datetime

from fastapi import APIRouter
from fastapi import Request

from src.core.config import config
from src.handlers.api.v1.health.models import HealthResponse

health_router = APIRouter(prefix='/health', tags=['health'])


@health_router.get('/', response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    started_at: datetime | None = getattr(request.app.state, 'start_time', None)
    uptime = (datetime.now(UTC) - started_at).total_seconds() if started_at else None

    return HealthResponse(
        app=config.APP_NAME,
        version=config.APP_VERSION,
        started_at=started_at,
        uptime_seconds=uptime,
    )

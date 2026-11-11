from datetime import datetime

from src.handlers.api.models import APIModel


class HealthResponse(APIModel):
    status: str = 'ok'
    app: str
    version: str
    started_at: datetime | None = None
    uptime_seconds: float | None = None

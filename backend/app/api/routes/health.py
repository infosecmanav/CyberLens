from fastapi import APIRouter, Request, Response, status

from app.db.session import database_is_ready
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
async def live(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get("/ready", response_model=HealthResponse)
async def ready(request: Request, response: Response) -> HealthResponse:
    settings = request.app.state.settings
    database_ready = await database_is_ready()
    if not database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if database_ready else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database="ready" if database_ready else "unavailable",
    )

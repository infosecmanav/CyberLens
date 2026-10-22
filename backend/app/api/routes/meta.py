from fastapi import APIRouter, Request

router = APIRouter(prefix="/meta", tags=["metadata"])


@router.get("")
async def metadata(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "api_prefix": settings.api_v1_prefix,
    }

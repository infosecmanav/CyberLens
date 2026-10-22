from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.dependencies import DatabaseSession
from app.models import Source
from app.models.enums import ImplementationStatus, SourceCategory
from app.schemas.source import SourceDetail, SourceListResponse, SourceSummary

router = APIRouter(prefix="/sources", tags=["intelligence sources"])


@router.get("", response_model=SourceListResponse)
async def list_sources(
    session: DatabaseSession,
    category: SourceCategory | None = None,
    implementation_status: ImplementationStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SourceListResponse:
    filters = []
    if category is not None:
        filters.append(Source.category == category)
    if implementation_status is not None:
        filters.append(Source.implementation_status == implementation_status)

    total = await session.scalar(select(func.count(Source.id)).where(*filters))
    items = (
        await session.scalars(
            select(Source)
            .where(*filters)
            .order_by(Source.category, Source.name)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    summaries = [SourceSummary.model_validate(item) for item in items]
    return SourceListResponse(items=summaries, total=total or 0, limit=limit, offset=offset)


@router.get("/{source_id}", response_model=SourceDetail)
async def get_source(source_id: str, session: DatabaseSession) -> Source:
    source = await session.scalar(select(Source).where(Source.source_id == source_id))
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


@router.get("/{source_id}/capabilities", response_model=list[dict[str, object]])
async def get_capabilities(source_id: str, session: DatabaseSession) -> list[dict[str, object]]:
    source = await session.scalar(select(Source).where(Source.source_id == source_id))
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return [
        {
            "operation": capability.operation,
            "entity_type": capability.entity_type,
            "enabled": capability.enabled,
            "notes": capability.notes,
        }
        for capability in source.capabilities
    ]

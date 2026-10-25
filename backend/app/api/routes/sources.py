import os
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select

from app.api.dependencies import AdminUser, DatabaseSession
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.connectors.models import ConnectorRequest, IntelligenceEntity
from app.intelligence.normalization import NormalizationError, normalize_entity
from app.models import Source
from app.models.enums import ImplementationStatus, SourceCategory, SourceHealth
from app.operations.audit import emit_audit
from app.schemas.source import (
    SourceDetail,
    SourceHealthResponse,
    SourceListResponse,
    SourceSummary,
    SourceTestRequest,
)

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


def _health_response(source: Source) -> SourceHealthResponse:
    configured = [name for name in source.environment_variables if os.getenv(name)]
    return SourceHealthResponse(
        source_id=source.source_id,
        health_status=source.health_status,
        required_environment_variables=source.environment_variables,
        configured_environment_variables=configured,
        last_checked=source.last_checked,
        last_success=source.last_success,
        message=source.last_error,
    )


@router.get("/{source_id}/health", response_model=SourceHealthResponse)
async def get_source_health(source_id: str, session: DatabaseSession) -> SourceHealthResponse:
    source = await session.scalar(select(Source).where(Source.source_id == source_id))
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return _health_response(source)


@router.post("/{source_id}/test", response_model=SourceHealthResponse)
async def test_source(
    source_id: str,
    payload: SourceTestRequest,
    request: Request,
    session: DatabaseSession,
    user: AdminUser,
) -> SourceHealthResponse:
    source = await session.scalar(select(Source).where(Source.source_id == source_id))
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    manager: ConnectorManager = request.app.state.connector_manager
    connector = manager.registry.get(source_id)
    if connector is None or not any(
        capability.operation == "lookup" and payload.entity_type.value in capability.entity_types
        for capability in (connector.manifest.capabilities if connector else [])
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source has no lookup capability for this entity type",
        )
    try:
        normalized = normalize_entity(payload.value, payload.entity_type)
    except NormalizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    results = await manager.lookup(
        ConnectorRequest(
            entity=IntelligenceEntity(
                entity_type=normalized.entity_type.value,
                value=normalized.normalized_value,
            )
        ),
        source_ids={source_id},
    )
    result = results[0]
    checked_at = datetime.now(UTC)
    source.last_checked = checked_at
    if result.outcome.value in {"SUCCESS", "NO_RESULT"}:
        source.health_status = SourceHealth.HEALTHY
        source.last_success = checked_at
        source.last_error = None
    elif result.outcome.value == "NOT_CONFIGURED":
        source.health_status = SourceHealth.NOT_CONFIGURED
        source.last_error = result.message or result.outcome.value
    else:
        source.health_status = SourceHealth.DEGRADED
        source.last_error = result.message or result.outcome.value
    emit_audit(
        session,
        actor_id=user.id,
        action="source.connection_tested",
        object_type="source",
        object_id=source.id,
        details={"source_id": source_id, "outcome": result.outcome.value},
    )
    await session.commit()
    response = _health_response(source)
    response.outcome = result.outcome
    response.message = result.message
    return response

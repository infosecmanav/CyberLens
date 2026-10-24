from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select

from app.api.dependencies import AnalystUser, DatabaseSession
from app.intelligence.collection import collect_entity
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.normalization import NormalizationError, normalize_entity
from app.models import Entity, Observation, Source
from app.models.enums import EntityType
from app.schemas.intelligence import (
    EntityListResponse,
    EntityResponse,
    LookupRequest,
    LookupResponse,
    LookupSourceResult,
    NormalizedEntityResponse,
    NormalizeRequest,
    ObservationResponse,
)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


def _normalize(payload: NormalizeRequest):  # type: ignore[no-untyped-def]
    try:
        return normalize_entity(payload.value, payload.entity_type)
    except NormalizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.post("/normalize", response_model=NormalizedEntityResponse)
async def normalize(payload: NormalizeRequest) -> NormalizedEntityResponse:
    normalized = _normalize(payload)
    return NormalizedEntityResponse(**normalized.model_dump())


@router.post("/lookup", response_model=LookupResponse)
async def lookup(
    payload: LookupRequest,
    request: Request,
    session: DatabaseSession,
    user: AnalystUser,
) -> LookupResponse:
    del user
    normalized = _normalize(payload)
    manager: ConnectorManager = request.app.state.connector_manager
    registered = {connector.manifest.source_id for connector in manager.registry.all()}
    if payload.source_ids is not None:
        unknown = sorted(set(payload.source_ids) - registered)
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown or unavailable connector: {', '.join(unknown)}",
            )
        selected: set[str] | None = set(payload.source_ids)
    elif payload.include_demo:
        selected = None
    else:
        selected = registered - {"local-fixtures"}

    entity, job, results, observation_ids = await collect_entity(
        session, manager, normalized, selected
    )
    source_results = []
    for result in results:
        ids = [
            observation_ids[(result.source_id, index)]
            for index in range(len(result.observations))
            if (result.source_id, index) in observation_ids
        ]
        source_results.append(
            LookupSourceResult(
                source_id=result.source_id,
                outcome=result.outcome,
                message=result.message,
                observation_ids=ids,
                retry_after_seconds=result.retry_after_seconds,
                raw_reference=result.raw_reference,
            )
        )
    assert job.completed_at is not None
    return LookupResponse(
        job_id=job.id,
        status=job.status,
        entity=EntityResponse.model_validate(entity),
        results=source_results,
        completed_at=job.completed_at,
    )


@router.get("/entities", response_model=EntityListResponse)
async def list_entities(
    session: DatabaseSession,
    entity_type: EntityType | None = None,
    query: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> EntityListResponse:
    filters = []
    if entity_type is not None:
        filters.append(Entity.entity_type == entity_type)
    if query:
        filters.append(Entity.normalized_value.ilike(f"%{query.strip()}%"))
    total = await session.scalar(select(func.count(Entity.id)).where(*filters))
    entities = (
        await session.scalars(
            select(Entity)
            .where(*filters)
            .order_by(Entity.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return EntityListResponse(
        items=[EntityResponse.model_validate(entity) for entity in entities],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: UUID, session: DatabaseSession) -> Entity:
    entity = await session.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return entity


@router.get("/entities/{entity_id}/observations", response_model=list[ObservationResponse])
async def get_entity_observations(
    entity_id: UUID, session: DatabaseSession
) -> list[ObservationResponse]:
    if await session.get(Entity, entity_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    rows = (
        await session.execute(
            select(Observation, Source.source_id)
            .join(Source, Source.id == Observation.source_id)
            .where(Observation.entity_id == entity_id)
            .order_by(Observation.observed_at.desc())
        )
    ).all()
    return [
        ObservationResponse(
            id=observation.id,
            source_id=source_id,
            observation_type=observation.observation_type,
            summary=observation.summary,
            observed_at=observation.observed_at,
            confidence=observation.confidence,
            source_reference=observation.source_reference,
            attributes=observation.raw_record,
        )
        for observation, source_id in rows
    ]

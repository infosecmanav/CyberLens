from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select, update

from app.api.dependencies import AnalystUser, DatabaseSession
from app.intelligence.collection import collect_entity
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.normalization import NormalizationError, normalize_entity
from app.intelligence.stix_import import (
    MAX_STIX_BUNDLE_BYTES,
    STIX_IMPORT_SOURCE_ID,
    StixImportFilterDefinition,
    canonical_bundle_size,
    import_stix_bundle,
)
from app.models import (
    Entity,
    Evidence,
    ImportBatch,
    ImportObjectOutcome,
    Observation,
    Source,
)
from app.models.enums import EntityType
from app.operations.audit import emit_audit
from app.schemas.intelligence import (
    EntityListResponse,
    EntityResponse,
    EvidencePromotionRequest,
    EvidencePromotionResponse,
    ImportBatchDetail,
    ImportBatchListResponse,
    ImportBatchSummary,
    ImportObjectOutcomeResponse,
    LookupRequest,
    LookupResponse,
    LookupSourceResult,
    NormalizedEntityResponse,
    NormalizeRequest,
    ObservationResponse,
    StixBundleImportRequest,
    StixImportedObservation,
    StixImportIssue,
    StixImportResponse,
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


@router.post("/imports/stix-bundles", response_model=StixImportResponse)
async def import_stix(
    payload: StixBundleImportRequest,
    session: DatabaseSession,
    user: AnalystUser,
) -> StixImportResponse:
    bundle = payload.bundle.model_dump()
    if canonical_bundle_size(bundle) > MAX_STIX_BUNDLE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="STIX bundle exceeds the 2 MiB import limit",
        )
    filter_definition = StixImportFilterDefinition(
        entity_types=frozenset(payload.filters.entity_types),
        minimum_confidence=payload.filters.minimum_confidence,
        valid_from_start=payload.filters.valid_from_start,
        valid_from_end=payload.filters.valid_from_end,
        required_marking_refs=frozenset(payload.filters.required_marking_refs),
    )
    summary = await import_stix_bundle(
        session,
        bundle_id=payload.bundle.id,
        objects=payload.bundle.objects,
        source_reference=str(payload.source_reference) if payload.source_reference else None,
        actor_id=user.id,
        filter_definition=filter_definition,
    )
    return StixImportResponse(
        import_id=summary.import_id,
        bundle_id=summary.bundle_id,
        source_id=STIX_IMPORT_SOURCE_ID,
        received_objects=summary.received_objects,
        accepted_objects=len(summary.items),
        imported_observations=summary.imported_observations,
        deduplicated_observations=summary.deduplicated_observations,
        created_entities=summary.created_entities,
        reused_entities=summary.reused_entities,
        rejected_objects=summary.rejected_objects,
        skipped_objects=summary.skipped_objects,
        filtered_objects=summary.filtered_objects,
        promoted_objects=0,
        filter_definition=filter_definition.as_record(),
        completed_at=summary.completed_at,
        items=[
            StixImportedObservation(
                entity_id=item.entity_id,
                observation_id=item.observation_id,
                entity_type=item.entity_type,
                normalized_value=item.normalized_value,
                external_id=item.external_id,
                deduplicated=item.deduplicated,
            )
            for item in summary.items
        ],
        issues=[
            StixImportIssue(
                object_index=issue.object_index,
                external_id=issue.external_id,
                disposition=issue.disposition,
                code=issue.code,
                message=issue.message,
            )
            for issue in summary.issues
        ],
    )


def _import_summary(batch: ImportBatch, source_id: str) -> ImportBatchSummary:
    return ImportBatchSummary(
        id=batch.id,
        bundle_id=batch.bundle_id,
        source_id=source_id,
        format=batch.format,
        status=batch.status,
        source_reference=batch.source_reference,
        received_objects=batch.received_objects,
        accepted_objects=batch.accepted_objects,
        imported_observations=batch.imported_observations,
        deduplicated_observations=batch.deduplicated_observations,
        created_entities=batch.created_entities,
        reused_entities=batch.reused_entities,
        rejected_objects=batch.rejected_objects,
        skipped_objects=batch.skipped_objects,
        filtered_objects=batch.filtered_objects,
        promoted_objects=batch.promoted_objects,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
    )


@router.get("/imports", response_model=ImportBatchListResponse)
async def list_imports(
    session: DatabaseSession,
    user: AnalystUser,
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(COMPLETED|COMPLETED_WITH_ISSUES)$",
    ),
    has_issues: bool | None = None,
    has_promotions: bool | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ImportBatchListResponse:
    del user
    filters = []
    if status_filter is not None:
        filters.append(ImportBatch.status == status_filter)
    issue_count = ImportBatch.rejected_objects + ImportBatch.skipped_objects
    if has_issues is True:
        filters.append(issue_count > 0)
    elif has_issues is False:
        filters.append(issue_count == 0)
    if has_promotions is True:
        filters.append(ImportBatch.promoted_objects > 0)
    elif has_promotions is False:
        filters.append(ImportBatch.promoted_objects == 0)
    total = await session.scalar(select(func.count(ImportBatch.id)).where(*filters))
    batches = list(
        (
            await session.scalars(
                select(ImportBatch)
                .where(*filters)
                .order_by(ImportBatch.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )
    source_ids = {batch.source_id for batch in batches}
    sources = {
        source.id: source.source_id
        for source in (
            await session.scalars(select(Source).where(Source.id.in_(source_ids)))
        ).all()
    }
    return ImportBatchListResponse(
        items=[
            _import_summary(batch, sources.get(batch.source_id, "unknown"))
            for batch in batches
        ],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/imports/{import_id}", response_model=ImportBatchDetail)
async def get_import(
    import_id: UUID,
    session: DatabaseSession,
    user: AnalystUser,
) -> ImportBatchDetail:
    del user
    batch = await session.get(ImportBatch, import_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    source = await session.get(Source, batch.source_id)
    summary = _import_summary(batch, source.source_id if source else "unknown")
    return ImportBatchDetail(
        **summary.model_dump(),
        bundle_hash=batch.bundle_hash,
        contract=batch.contract,
        filter_definition=batch.filter_definition,
        objects=[
            ImportObjectOutcomeResponse(
                id=item.id,
                object_index=item.object_index,
                external_id=item.external_id,
                disposition=item.disposition,
                code=item.code,
                message=item.message,
                entity_id=item.entity_id,
                observation_id=item.observation_id,
                evidence_id=item.evidence_id,
                content_hash=item.content_hash,
                raw_record=item.raw_record,
            )
            for item in batch.objects
        ],
    )


@router.post(
    "/imports/{import_id}/objects/{object_outcome_id}/promote",
    response_model=EvidencePromotionResponse,
)
async def promote_import_object(
    import_id: UUID,
    object_outcome_id: UUID,
    payload: EvidencePromotionRequest,
    session: DatabaseSession,
    user: AnalystUser,
) -> EvidencePromotionResponse:
    batch = await session.get(ImportBatch, import_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    outcome = await session.scalar(
        select(ImportObjectOutcome)
        .where(
            ImportObjectOutcome.id == object_outcome_id,
            ImportObjectOutcome.import_batch_id == batch.id,
        )
        .with_for_update()
    )
    if outcome is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import object outcome not found",
        )
    if outcome.disposition not in {"IMPORTED", "DEDUPLICATED"} or outcome.observation_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only accepted import outcomes can be promoted to evidence",
        )
    if outcome.evidence_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This import outcome has already been promoted to evidence",
        )
    observation = await session.get(Observation, outcome.observation_id)
    if observation is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The linked observation is no longer available",
        )
    reviewed_at = datetime.now(UTC)
    evidence = Evidence(
        observation_id=observation.id,
        polarity=payload.polarity,
        assessment_dimension=payload.assessment_dimension,
        claim=payload.claim,
        uncertainty_notes=payload.uncertainty_notes,
        analyst_reviewed_at=reviewed_at,
        promoted_by=user.id,
    )
    session.add(evidence)
    await session.flush()
    outcome.evidence_id = evidence.id
    await session.execute(
        update(ImportBatch)
        .where(ImportBatch.id == batch.id)
        .values(promoted_objects=ImportBatch.promoted_objects + 1)
    )
    emit_audit(
        session,
        actor_id=user.id,
        action="intelligence.import_object_promoted",
        object_type="evidence",
        object_id=evidence.id,
        details={
            "import_id": str(batch.id),
            "object_outcome_id": str(outcome.id),
            "observation_id": str(observation.id),
            "polarity": payload.polarity.value,
            "assessment_dimension": payload.assessment_dimension.value,
        },
    )
    await session.commit()
    return EvidencePromotionResponse(
        evidence_id=evidence.id,
        import_id=batch.id,
        object_outcome_id=outcome.id,
        observation_id=observation.id,
        polarity=evidence.polarity,
        assessment_dimension=evidence.assessment_dimension,
        claim=evidence.claim,
        uncertainty_notes=evidence.uncertainty_notes or "",
        promoted_by=user.id,
        analyst_reviewed_at=reviewed_at,
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

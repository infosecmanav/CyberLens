from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select

from app.api.dependencies import AnalystUser, DatabaseSession
from app.correlation import build_investigation_graph, calculate_similarity
from app.intelligence.collection import get_or_create_entity
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.normalization import NormalizationError, normalize_entity
from app.investigations import (
    plan_investigation,
    reconcile_investigation_evidence,
    run_investigation,
)
from app.models import (
    AnalystDecision,
    Assessment,
    Entity,
    Evidence,
    Finding,
    Investigation,
    InvestigationEntity,
    InvestigationEvent,
    InvestigationStep,
    Observation,
    Source,
)
from app.models.enums import EntityType, InvestigationStatus, StepStatus
from app.operations import emit_audit
from app.schemas.operations import (
    AnalystDecisionCreate,
    AnalystDecisionResponse,
    AssessmentResponse,
    EvidenceResponse,
    FindingResponse,
    InvestigationCreate,
    InvestigationDetail,
    InvestigationEventResponse,
    InvestigationGraph,
    InvestigationListResponse,
    InvestigationResponse,
    InvestigationStepResponse,
    SimilarityResponse,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])


async def _load(session: DatabaseSession, investigation_id: UUID) -> Investigation:
    investigation = await session.get(Investigation, investigation_id)
    if investigation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    return investigation


async def _detail(session: DatabaseSession, investigation: Investigation) -> InvestigationDetail:
    await session.refresh(investigation)
    steps = list(
        (
            await session.scalars(
                select(InvestigationStep)
                .where(InvestigationStep.investigation_id == investigation.id)
                .order_by(InvestigationStep.sequence)
            )
        ).all()
    )
    findings = list(
        (
            await session.scalars(
                select(Finding)
                .where(Finding.investigation_id == investigation.id)
                .order_by(Finding.created_at)
            )
        ).all()
    )
    assessments = list(
        (
            await session.scalars(
                select(Assessment)
                .where(Assessment.investigation_id == investigation.id)
                .order_by(Assessment.created_at)
            )
        ).all()
    )
    decisions = list(
        (
            await session.scalars(
                select(AnalystDecision)
                .where(AnalystDecision.investigation_id == investigation.id)
                .order_by(AnalystDecision.decided_at)
            )
        ).all()
    )
    events = list(
        (
            await session.scalars(
                select(InvestigationEvent)
                .where(InvestigationEvent.investigation_id == investigation.id)
                .order_by(InvestigationEvent.occurred_at)
            )
        ).all()
    )
    base = InvestigationResponse.model_validate(investigation).model_dump()
    return InvestigationDetail(
        **base,
        steps=[InvestigationStepResponse.model_validate(item) for item in steps],
        findings=[FindingResponse.model_validate(item) for item in findings],
        assessments=[AssessmentResponse.model_validate(item) for item in assessments],
        decisions=[AnalystDecisionResponse.model_validate(item) for item in decisions],
        events=[InvestigationEventResponse.model_validate(item) for item in events],
    )


@router.get("", response_model=InvestigationListResponse)
async def list_investigations(
    session: DatabaseSession,
    investigation_status: Annotated[
        InvestigationStatus | None, Query(alias="status")
    ] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> InvestigationListResponse:
    filters = []
    if investigation_status is not None:
        filters.append(Investigation.status == investigation_status)
    total = await session.scalar(select(func.count(Investigation.id)).where(*filters))
    items = list(
        (
            await session.scalars(
                select(Investigation)
                .where(*filters)
                .order_by(Investigation.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )
    return InvestigationListResponse(
        items=[InvestigationResponse.model_validate(item) for item in items],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=InvestigationDetail, status_code=status.HTTP_201_CREATED)
async def create_investigation(
    payload: InvestigationCreate,
    request: Request,
    session: DatabaseSession,
    user: AnalystUser,
) -> InvestigationDetail:
    manager: ConnectorManager = request.app.state.connector_manager
    registered = {connector.manifest.source_id for connector in manager.registry.all()}
    if payload.source_ids:
        unknown = sorted(set(payload.source_ids) - registered)
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown or unavailable connector: {', '.join(unknown)}",
            )
    seed_entity: Entity | None = None
    if payload.seed_value is not None:
        try:
            entity_type = EntityType(payload.seed_entity_type) if payload.seed_entity_type else None
            normalized = normalize_entity(payload.seed_value, entity_type)
        except (NormalizationError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc
        seed_entity = await get_or_create_entity(session, normalized)
    investigation = Investigation(
        title=payload.title.strip(),
        objective=payload.objective.strip(),
        workflow_type=payload.workflow_type.upper(),
        status=InvestigationStatus.PLANNING,
        seed_entity_id=seed_entity.id if seed_entity else None,
        created_by=user.id,
        limitations=[],
        budgets=payload.budgets.model_dump(),
        budget_usage={"api_requests": 0, "entities": 1 if seed_entity else 0, "cost_usd": 0.0},
        input_context={
            "source_ids": payload.source_ids,
            "include_demo": payload.include_demo,
            "objective_is_untrusted_text": True,
        },
    )
    session.add(investigation)
    await session.flush()
    if seed_entity is not None:
        session.add(
            InvestigationEntity(
                investigation_id=investigation.id,
                entity_id=seed_entity.id,
                role="SEED",
            )
        )
    emit_audit(
        session,
        actor_id=user.id,
        action="INVESTIGATION_CREATED",
        object_type="Investigation",
        object_id=investigation.id,
        details={"workflow_type": investigation.workflow_type},
    )
    await session.commit()
    await plan_investigation(session, investigation)
    await session.refresh(investigation)
    return await _detail(session, investigation)


@router.get("/{investigation_id}", response_model=InvestigationDetail)
async def get_investigation(
    investigation_id: UUID, session: DatabaseSession
) -> InvestigationDetail:
    return await _detail(session, await _load(session, investigation_id))


@router.post("/{investigation_id}/run", response_model=InvestigationDetail)
async def run(
    investigation_id: UUID,
    request: Request,
    session: DatabaseSession,
    user: AnalystUser,
) -> InvestigationDetail:
    investigation = await _load(session, investigation_id)
    if investigation.status == InvestigationStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resume the cancelled investigation before running it",
        )
    manager: ConnectorManager = request.app.state.connector_manager
    await run_investigation(session, manager, investigation)
    emit_audit(
        session,
        actor_id=user.id,
        action="INVESTIGATION_RUN",
        object_type="Investigation",
        object_id=investigation.id,
        details={"status": investigation.status.value},
    )
    await session.commit()
    return await _detail(session, investigation)


@router.post("/{investigation_id}/reconcile", response_model=InvestigationDetail)
async def reconcile(
    investigation_id: UUID, session: DatabaseSession, user: AnalystUser
) -> InvestigationDetail:
    investigation = await _load(session, investigation_id)
    if investigation.status != InvestigationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence reconciliation requires a completed investigation",
        )
    if investigation.seed_entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence reconciliation requires a seed entity",
        )
    result = await reconcile_investigation_evidence(session, investigation)
    emit_audit(
        session,
        actor_id=user.id,
        action="EVIDENCE_RECONCILED",
        object_type="Investigation",
        object_id=investigation.id,
        details={
            "status": result["cross_validation_status"],
            "provenance_groups": result["provenance_groups"],
        },
    )
    await session.commit()
    return await _detail(session, investigation)


@router.post("/{investigation_id}/cancel", response_model=InvestigationDetail)
async def cancel(
    investigation_id: UUID, session: DatabaseSession, user: AnalystUser
) -> InvestigationDetail:
    investigation = await _load(session, investigation_id)
    if investigation.status == InvestigationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A completed investigation cannot be cancelled",
        )
    investigation.status = InvestigationStatus.CANCELLED
    pending = list(
        (
            await session.scalars(
                select(InvestigationStep).where(
                    InvestigationStep.investigation_id == investigation.id,
                    InvestigationStep.status.in_([StepStatus.PENDING, StepStatus.RUNNING]),
                )
            )
        ).all()
    )
    for step in pending:
        step.status = StepStatus.CANCELLED
        step.completed_at = datetime.now(UTC)
    session.add(
        InvestigationEvent(
            investigation_id=investigation.id,
            occurred_at=datetime.now(UTC),
            event_type="CANCELLED",
            message="Investigation cancelled by an analyst.",
            details={},
        )
    )
    emit_audit(
        session,
        actor_id=user.id,
        action="INVESTIGATION_CANCELLED",
        object_type="Investigation",
        object_id=investigation.id,
    )
    await session.commit()
    return await _detail(session, investigation)


@router.post("/{investigation_id}/resume", response_model=InvestigationDetail)
async def resume(
    investigation_id: UUID,
    request: Request,
    session: DatabaseSession,
    user: AnalystUser,
) -> InvestigationDetail:
    investigation = await _load(session, investigation_id)
    if investigation.status not in {
        InvestigationStatus.CANCELLED,
        InvestigationStatus.FAILED,
        InvestigationStatus.WAITING_FOR_ANALYST,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only cancelled, failed, or budget-stopped investigations can resume",
        )
    steps = list(
        (
            await session.scalars(
                select(InvestigationStep).where(
                    InvestigationStep.investigation_id == investigation.id,
                    InvestigationStep.status.in_([StepStatus.CANCELLED, StepStatus.FAILED]),
                )
            )
        ).all()
    )
    for step in steps:
        step.status = StepStatus.PENDING
        step.error = None
        step.completed_at = None
    investigation.status = InvestigationStatus.PLANNING
    investigation.error = None
    await session.commit()
    manager: ConnectorManager = request.app.state.connector_manager
    await run_investigation(session, manager, investigation)
    emit_audit(
        session,
        actor_id=user.id,
        action="INVESTIGATION_RESUMED",
        object_type="Investigation",
        object_id=investigation.id,
    )
    await session.commit()
    return await _detail(session, investigation)


@router.post("/{investigation_id}/decisions", response_model=AnalystDecisionResponse)
async def record_decision(
    investigation_id: UUID,
    payload: AnalystDecisionCreate,
    session: DatabaseSession,
    user: AnalystUser,
) -> AnalystDecision:
    investigation = await _load(session, investigation_id)
    previous = await session.scalar(
        select(AnalystDecision)
        .where(AnalystDecision.investigation_id == investigation.id)
        .order_by(AnalystDecision.decided_at.desc())
    )
    decision = AnalystDecision(
        investigation_id=investigation.id,
        verdict=payload.verdict,
        rationale=payload.rationale.strip(),
        decided_by=user.id,
        decided_at=datetime.now(UTC),
        supersedes_id=previous.id if previous else None,
    )
    session.add(decision)
    investigation.verdict = payload.verdict
    emit_audit(
        session,
        actor_id=user.id,
        action="ANALYST_DECISION_RECORDED",
        object_type="Investigation",
        object_id=investigation.id,
        details={"verdict": payload.verdict.value},
    )
    await session.commit()
    await session.refresh(decision)
    return decision


@router.get("/{investigation_id}/findings", response_model=list[FindingResponse])
async def findings(investigation_id: UUID, session: DatabaseSession) -> list[Finding]:
    await _load(session, investigation_id)
    return list(
        (
            await session.scalars(
                select(Finding)
                .where(Finding.investigation_id == investigation_id)
                .order_by(Finding.created_at)
            )
        ).all()
    )


@router.get("/{investigation_id}/evidence", response_model=list[EvidenceResponse])
async def evidence(investigation_id: UUID, session: DatabaseSession) -> list[EvidenceResponse]:
    investigation = await _load(session, investigation_id)
    if investigation.seed_entity_id is None:
        return []
    rows = (
        await session.execute(
            select(Evidence, Observation, Source.source_id)
            .join(Observation, Observation.id == Evidence.observation_id)
            .join(Source, Source.id == Observation.source_id)
            .where(Observation.entity_id == investigation.seed_entity_id)
            .order_by(Observation.observed_at.desc())
        )
    ).all()
    return [
        EvidenceResponse(
            id=item.id,
            observation_id=observation.id,
            source_id=source_id,
            polarity=item.polarity.value,
            claim=item.claim,
            uncertainty_notes=item.uncertainty_notes,
            observed_at=observation.observed_at,
            source_reference=observation.source_reference,
        )
        for item, observation, source_id in rows
    ]


@router.get("/{investigation_id}/timeline", response_model=list[InvestigationEventResponse])
async def timeline(
    investigation_id: UUID, session: DatabaseSession
) -> list[InvestigationEvent]:
    await _load(session, investigation_id)
    return list(
        (
            await session.scalars(
                select(InvestigationEvent)
                .where(InvestigationEvent.investigation_id == investigation_id)
                .order_by(InvestigationEvent.occurred_at)
            )
        ).all()
    )


@router.get("/{investigation_id}/graph", response_model=InvestigationGraph)
async def graph(
    investigation_id: UUID,
    session: DatabaseSession,
    max_depth: int = Query(default=2, ge=0, le=5),
    max_nodes: int = Query(default=100, ge=1, le=500),
) -> InvestigationGraph:
    investigation = await _load(session, investigation_id)
    nodes, edges, truncated = await build_investigation_graph(
        session, investigation, max_depth, max_nodes
    )
    return InvestigationGraph(
        nodes=nodes,
        edges=edges,
        truncated=truncated,
        max_depth=max_depth,
    )


@router.get("/{investigation_id}/similar", response_model=list[SimilarityResponse])
async def similar(
    investigation_id: UUID, session: DatabaseSession
) -> list[SimilarityResponse]:
    investigation = await _load(session, investigation_id)
    scores = await calculate_similarity(session, investigation)
    return [
        SimilarityResponse(
            investigation_id=score.target_investigation_id,
            score=score.score,
            shared_factors=score.shared_factors,
            limitation=score.limitation,
        )
        for score in scores
    ]

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.dependencies import AdminUser, DatabaseSession
from app.models import (
    AuditEvent,
    Case,
    DetectionCandidate,
    IntelligenceChange,
    Investigation,
    Observation,
    Source,
)
from app.models.enums import (
    CaseStatus,
    DetectionValidationStatus,
    InvestigationStatus,
    SourceHealth,
)
from app.schemas.operations import OperationsMetrics

router = APIRouter(tags=["operations"])


@router.get("/operations/metrics", response_model=OperationsMetrics)
async def metrics(session: DatabaseSession) -> OperationsMetrics:
    source_total = await session.scalar(select(func.count(Source.id)))
    sources_healthy = await session.scalar(
        select(func.count(Source.id)).where(Source.health_status == SourceHealth.HEALTHY)
    )
    investigations_total = await session.scalar(select(func.count(Investigation.id)))
    investigations_running = await session.scalar(
        select(func.count(Investigation.id)).where(
            Investigation.status.not_in(
                [
                    InvestigationStatus.COMPLETED,
                    InvestigationStatus.CANCELLED,
                    InvestigationStatus.FAILED,
                    InvestigationStatus.WAITING_FOR_ANALYST,
                ]
            )
        )
    )
    open_cases = await session.scalar(
        select(func.count(Case.id)).where(
            Case.status.in_([CaseStatus.OPEN, CaseStatus.IN_PROGRESS, CaseStatus.BLOCKED])
        )
    )
    actionable_changes = await session.scalar(
        select(func.count(IntelligenceChange.id)).where(
            IntelligenceChange.is_actionable.is_(True),
            IntelligenceChange.acknowledged_at.is_(None),
        )
    )
    detection_candidates = await session.scalar(select(func.count(DetectionCandidate.id)))
    validated_detections = await session.scalar(
        select(func.count(DetectionCandidate.id)).where(
            DetectionCandidate.validation_status.in_(
                [
                    DetectionValidationStatus.VALIDATED_IN_TEST,
                    DetectionValidationStatus.VALIDATED_IN_PRODUCTION,
                ]
            )
        )
    )
    demonstration_records = await session.scalar(
        select(func.count(Observation.id)).where(
            Observation.observation_type == "DEMONSTRATION_ONLY"
        )
    )
    return OperationsMetrics(
        source_total=source_total or 0,
        sources_healthy=sources_healthy or 0,
        investigations_total=investigations_total or 0,
        investigations_running=investigations_running or 0,
        open_cases=open_cases or 0,
        actionable_changes=actionable_changes or 0,
        detection_candidates=detection_candidates or 0,
        validated_detections=validated_detections or 0,
        demonstration_records=demonstration_records or 0,
    )


@router.get("/audit", response_model=list[dict[str, object]])
async def audit_events(
    session: DatabaseSession,
    user: AdminUser,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, object]]:
    del user
    events = list(
        (
            await session.scalars(
                select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit)
            )
        ).all()
    )
    return [
        {
            "id": event.id,
            "occurred_at": event.occurred_at,
            "actor_id": event.actor_id,
            "action": event.action,
            "object_type": event.object_type,
            "object_id": event.object_id,
            "details": event.details,
        }
        for event in events
    ]

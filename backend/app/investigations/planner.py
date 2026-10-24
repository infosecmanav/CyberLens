from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Investigation, InvestigationEvent, InvestigationStep
from app.models.enums import InvestigationStatus, StepStatus

DEFAULT_BUDGETS: dict[str, int | float] = {
    "runtime_seconds": 60,
    "api_requests": 10,
    "entities": 50,
    "graph_depth": 2,
    "pivot_depth": 1,
    "reports": 20,
    "cost_usd": 0.0,
}

PLAN: tuple[tuple[InvestigationStatus, str, str, str], ...] = (
    (
        InvestigationStatus.COLLECTING,
        "Collect applicable intelligence",
        "Use capability routing and the configured request budget for the seed entity.",
        "collect",
    ),
    (
        InvestigationStatus.VALIDATING,
        "Cross-validate source observations",
        "Convert source-backed observations into explicit supporting or contextual evidence.",
        "validate",
    ),
    (
        InvestigationStatus.CORRELATING,
        "Correlate bounded entity context",
        "Create only relationships supported by collected records and preserve uncertainty.",
        "correlate",
    ),
    (
        InvestigationStatus.PRIORITIZING,
        "Create a heuristic assessment",
        "Keep confidence dimensions separate and record limitations before assigning a verdict.",
        "assess",
    ),
    (
        InvestigationStatus.DETECTION_ANALYSIS,
        "Evaluate detection readiness",
        "Identify whether evidence and telemetry assumptions are sufficient for a draft candidate.",
        "detection-readiness",
    ),
)


async def plan_investigation(
    session: AsyncSession, investigation: Investigation
) -> list[InvestigationStep]:
    existing = (
        await session.scalars(
            select(InvestigationStep)
            .where(InvestigationStep.investigation_id == investigation.id)
            .order_by(InvestigationStep.sequence)
        )
    ).all()
    if existing:
        return list(existing)
    steps = []
    for sequence, (phase, title, reason, key) in enumerate(PLAN, start=1):
        step = InvestigationStep(
            investigation_id=investigation.id,
            sequence=sequence,
            phase=phase,
            status=StepStatus.PENDING,
            title=title,
            operational_reason=reason,
            idempotency_key=key,
        )
        session.add(step)
        steps.append(step)
    session.add(
        InvestigationEvent(
            investigation_id=investigation.id,
            occurred_at=datetime.now(UTC),
            event_type="PLAN_CREATED",
            message="Deterministic investigation plan created.",
            details={"planner_version": investigation.planner_version, "step_count": len(steps)},
        )
    )
    await session.commit()
    return steps

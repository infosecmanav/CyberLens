from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.dependencies import AnalystUser, DatabaseSession
from app.intelligence.connectors.manager import ConnectorManager
from app.models import Entity, IntelligenceChange, MonitoringObjective, MonitoringRun
from app.operations import emit_audit
from app.operations.monitoring import run_due_objectives, run_monitoring_objective
from app.schemas.operations import (
    IntelligenceChangeResponse,
    MonitoringObjectiveCreate,
    MonitoringObjectiveResponse,
    MonitoringRunResponse,
)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


async def _objective(session: DatabaseSession, objective_id: UUID) -> MonitoringObjective:
    objective = await session.get(MonitoringObjective, objective_id)
    if objective is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Monitoring objective not found"
        )
    return objective


@router.get("", response_model=list[MonitoringObjectiveResponse])
async def list_objectives(session: DatabaseSession) -> list[MonitoringObjective]:
    return list(
        (
            await session.scalars(
                select(MonitoringObjective).order_by(MonitoringObjective.updated_at.desc())
            )
        ).all()
    )


@router.post("", response_model=MonitoringObjectiveResponse, status_code=status.HTTP_201_CREATED)
async def create_objective(
    payload: MonitoringObjectiveCreate,
    session: DatabaseSession,
    user: AnalystUser,
) -> MonitoringObjective:
    if payload.entity_id and await session.get(Entity, payload.entity_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    objective = MonitoringObjective(
        name=payload.name.strip(),
        objective=payload.objective.strip(),
        entity_id=payload.entity_id,
        cadence_minutes=payload.cadence_minutes,
        created_by=user.id,
    )
    session.add(objective)
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="MONITORING_OBJECTIVE_CREATED",
        object_type="MonitoringObjective",
        object_id=objective.id,
    )
    await session.commit()
    await session.refresh(objective)
    return objective


@router.post("/{objective_id}/run", response_model=MonitoringRunResponse)
async def run_objective(
    objective_id: UUID,
    request: Request,
    session: DatabaseSession,
    user: AnalystUser,
) -> MonitoringRunResponse:
    objective = await _objective(session, objective_id)
    manager: ConnectorManager = request.app.state.connector_manager
    run = await run_monitoring_objective(session, manager, objective)
    emit_audit(
        session,
        actor_id=user.id,
        action="MONITORING_RUN_COMPLETED",
        object_type="MonitoringRun",
        object_id=run.id,
        details={"status": run.status.value},
    )
    await session.commit()
    return MonitoringRunResponse.model_validate(run)


@router.post("/due/run", response_model=list[MonitoringRunResponse])
async def run_due(
    request: Request,
    session: DatabaseSession,
    user: AnalystUser,
) -> list[MonitoringRunResponse]:
    manager: ConnectorManager = request.app.state.connector_manager
    runs = await run_due_objectives(session, manager)
    for item in runs:
        emit_audit(
            session,
            actor_id=user.id,
            action="DUE_MONITORING_RUN_COMPLETED",
            object_type="MonitoringRun",
            object_id=item.id,
            details={"status": item.status.value},
        )
    await session.commit()
    return [MonitoringRunResponse.model_validate(item) for item in runs]


@router.get("/changes", response_model=list[IntelligenceChangeResponse])
async def list_changes(
    session: DatabaseSession, actionable_only: bool = False
) -> list[IntelligenceChange]:
    filters = []
    if actionable_only:
        filters.append(IntelligenceChange.is_actionable.is_(True))
    return list(
        (
            await session.scalars(
                select(IntelligenceChange)
                .join(MonitoringRun, MonitoringRun.id == IntelligenceChange.run_id)
                .where(*filters)
                .order_by(MonitoringRun.started_at.desc())
            )
        ).all()
    )


@router.post("/changes/{change_id}/acknowledge", response_model=IntelligenceChangeResponse)
async def acknowledge_change(
    change_id: UUID, session: DatabaseSession, user: AnalystUser
) -> IntelligenceChange:
    change = await session.get(IntelligenceChange, change_id)
    if change is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change not found")
    change.acknowledged_at = datetime.now(UTC)
    emit_audit(
        session,
        actor_id=user.id,
        action="INTELLIGENCE_CHANGE_ACKNOWLEDGED",
        object_type="IntelligenceChange",
        object_id=change.id,
    )
    await session.commit()
    await session.refresh(change)
    return change

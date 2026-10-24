from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import AnalystUser, DatabaseSession
from app.models import ApprovalRequest, Case, Investigation, Playbook, PlaybookExecution
from app.models.enums import ApprovalStatus, PlaybookExecutionStatus
from app.operations import emit_audit
from app.schemas.operations import (
    PlaybookExecutionCreate,
    PlaybookExecutionResponse,
    PlaybookResponse,
)

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


@router.get("", response_model=list[PlaybookResponse])
async def list_playbooks(session: DatabaseSession) -> list[Playbook]:
    return list(
        (
            await session.scalars(
                select(Playbook).where(Playbook.is_active.is_(True)).order_by(Playbook.name)
            )
        ).all()
    )


@router.post(
    "/{playbook_id}/executions",
    response_model=PlaybookExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def execute_playbook(
    playbook_id: UUID,
    payload: PlaybookExecutionCreate,
    session: DatabaseSession,
    user: AnalystUser,
) -> PlaybookExecution:
    playbook = await session.get(Playbook, playbook_id)
    if playbook is None or not playbook.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")
    if payload.case_id and await session.get(Case, payload.case_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if payload.investigation_id and await session.get(
        Investigation, payload.investigation_id
    ) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    execution = PlaybookExecution(
        playbook_id=playbook.id,
        case_id=payload.case_id,
        investigation_id=payload.investigation_id,
        status=PlaybookExecutionStatus.RUNNING,
        dry_run=True,
        current_step=0,
        events=[],
        started_at=datetime.now(UTC),
        started_by=user.id,
    )
    session.add(execution)
    await session.flush()
    events: list[dict[str, object]] = []
    for index, step in enumerate(playbook.steps):
        if bool(step.get("high_impact", False)):
            execution.status = PlaybookExecutionStatus.WAITING_APPROVAL
            session.add(
                ApprovalRequest(
                    execution_id=execution.id,
                    action=str(step.get("action", "HIGH_IMPACT_ACTION")),
                    risk_summary="High-impact playbook step requires explicit human approval.",
                    status=ApprovalStatus.PENDING,
                    requested_by=user.id,
                )
            )
            events.append({"step": index, "status": "WAITING_APPROVAL"})
            break
        execution.current_step = index + 1
        events.append(
            {
                "step": index,
                "name": str(step.get("name", "Unnamed step")),
                "status": "DRY_RUN_COMPLETED",
                "external_action_performed": False,
            }
        )
    else:
        execution.status = PlaybookExecutionStatus.COMPLETED
        execution.completed_at = datetime.now(UTC)
    execution.events = events
    emit_audit(
        session,
        actor_id=user.id,
        action="PLAYBOOK_EXECUTED",
        object_type="PlaybookExecution",
        object_id=execution.id,
        details={"status": execution.status.value, "dry_run": True},
    )
    await session.commit()
    await session.refresh(execution)
    return execution


@router.get("/executions", response_model=list[PlaybookExecutionResponse])
async def list_executions(session: DatabaseSession) -> list[PlaybookExecution]:
    return list(
        (
            await session.scalars(
                select(PlaybookExecution).order_by(PlaybookExecution.created_at.desc())
            )
        ).all()
    )

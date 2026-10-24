from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import AdminUser, AnalystUser, DatabaseSession
from app.models import ApprovalRequest, Case, CaseTask, Investigation
from app.models.enums import ApprovalStatus, CaseStatus, TaskStatus
from app.operations import emit_audit
from app.schemas.operations import (
    ApprovalCreate,
    ApprovalResolve,
    ApprovalResponse,
    CaseCreate,
    CaseResponse,
    TaskCreate,
    TaskResponse,
)

router = APIRouter(prefix="/cases", tags=["cases"])


async def _case(session: DatabaseSession, case_id: UUID) -> Case:
    item = await session.get(Case, case_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return item


async def _task(session: DatabaseSession, task_id: UUID) -> CaseTask:
    item = await session.get(CaseTask, task_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return item


@router.get("", response_model=list[CaseResponse])
async def list_cases(
    session: DatabaseSession,
    case_status: Annotated[CaseStatus | None, Query(alias="status")] = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[Case]:
    filters = []
    if case_status is not None:
        filters.append(Case.status == case_status)
    return list(
        (
            await session.scalars(
                select(Case).where(*filters).order_by(Case.updated_at.desc()).limit(limit)
            )
        ).all()
    )


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CaseCreate, session: DatabaseSession, user: AnalystUser
) -> Case:
    if payload.investigation_id and await session.get(
        Investigation, payload.investigation_id
    ) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    item = Case(
        title=payload.title.strip(),
        summary=payload.summary.strip(),
        status=CaseStatus.OPEN,
        priority=payload.priority,
        investigation_id=payload.investigation_id,
        owner_id=payload.owner_id,
        created_by=user.id,
    )
    session.add(item)
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="CASE_CREATED",
        object_type="Case",
        object_id=item.id,
        details={"priority": item.priority.value},
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: UUID, session: DatabaseSession) -> Case:
    return await _case(session, case_id)


@router.get("/{case_id}/tasks", response_model=list[TaskResponse])
async def list_tasks(case_id: UUID, session: DatabaseSession) -> list[CaseTask]:
    await _case(session, case_id)
    return list(
        (
            await session.scalars(
                select(CaseTask)
                .where(CaseTask.case_id == case_id)
                .order_by(CaseTask.created_at)
            )
        ).all()
    )


@router.post("/{case_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    case_id: UUID,
    payload: TaskCreate,
    session: DatabaseSession,
    user: AnalystUser,
) -> CaseTask:
    item_case = await _case(session, case_id)
    task = CaseTask(
        case_id=item_case.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        owner_id=payload.owner_id,
        due_at=payload.due_at,
        action_type=payload.action_type.upper(),
        high_impact=payload.high_impact,
        dry_run=True,
    )
    session.add(task)
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="CASE_TASK_CREATED",
        object_type="CaseTask",
        object_id=task.id,
        details={"high_impact": task.high_impact},
    )
    await session.commit()
    await session.refresh(task)
    return task


@router.post("/tasks/{task_id}/approval", response_model=ApprovalResponse)
async def request_approval(
    task_id: UUID,
    payload: ApprovalCreate,
    session: DatabaseSession,
    user: AnalystUser,
) -> ApprovalRequest:
    task = await _task(session, task_id)
    if not task.high_impact:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This task is safe and does not require high-impact approval",
        )
    pending = await session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.task_id == task.id,
            ApprovalRequest.status == ApprovalStatus.PENDING,
        )
    )
    if pending is not None:
        return pending
    approval = ApprovalRequest(
        task_id=task.id,
        action=task.action_type,
        risk_summary=payload.risk_summary.strip(),
        status=ApprovalStatus.PENDING,
        requested_by=user.id,
    )
    session.add(approval)
    task.status = TaskStatus.WAITING_APPROVAL
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="APPROVAL_REQUESTED",
        object_type="ApprovalRequest",
        object_id=approval.id,
        details={"action": approval.action},
    )
    await session.commit()
    await session.refresh(approval)
    return approval


@router.post("/approvals/{approval_id}/resolve", response_model=ApprovalResponse)
async def resolve_approval(
    approval_id: UUID,
    payload: ApprovalResolve,
    session: DatabaseSession,
    user: AdminUser,
) -> ApprovalRequest:
    approval = await session.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Approval is already resolved"
        )
    approval.status = payload.status
    approval.resolved_by = user.id
    approval.resolution_rationale = payload.rationale.strip()
    approval.resolved_at = datetime.now(UTC)
    if approval.task_id:
        task = await session.get(CaseTask, approval.task_id)
        if task is not None:
            task.status = (
                TaskStatus.OPEN
                if payload.status == ApprovalStatus.APPROVED
                else TaskStatus.CANCELLED
            )
    emit_audit(
        session,
        actor_id=user.id,
        action="APPROVAL_RESOLVED",
        object_type="ApprovalRequest",
        object_id=approval.id,
        details={"status": payload.status.value},
    )
    await session.commit()
    await session.refresh(approval)
    return approval


@router.post("/tasks/{task_id}/execute", response_model=TaskResponse)
async def execute_task(
    task_id: UUID, session: DatabaseSession, user: AnalystUser
) -> CaseTask:
    task = await _task(session, task_id)
    if task.high_impact:
        approved = await session.scalar(
            select(ApprovalRequest).where(
                ApprovalRequest.task_id == task.id,
                ApprovalRequest.status == ApprovalStatus.APPROVED,
            )
        )
        if approved is None:
            task.status = TaskStatus.WAITING_APPROVAL
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="High-impact action requires an approved request",
            )
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(UTC)
    task.dry_run = True
    emit_audit(
        session,
        actor_id=user.id,
        action="TASK_DRY_RUN_COMPLETED",
        object_type="CaseTask",
        object_id=task.id,
        details={"external_action_performed": False},
    )
    await session.commit()
    await session.refresh(task)
    return task

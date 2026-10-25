from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.dependencies import AdminUser, AnalystUser, DatabaseSession
from app.intelligence.export import (
    ExportValidationError,
    build_export_bundle,
    bundle_hash,
    export_candidate,
    validate_candidate,
    validate_frozen_bundle,
)
from app.intelligence.taxii import TaxiiClient, TaxiiError
from app.models import (
    ApprovalRequest,
    Evidence,
    TaxiiCollection,
    TaxiiExportPolicy,
    TaxiiExportRequest,
)
from app.models.enums import ApprovalStatus, ExportStatus
from app.operations.audit import emit_audit
from app.schemas.export import (
    EligibleExportEvidence,
    ExportApprovalResolve,
    ExportPolicyCreate,
    ExportPolicyResponse,
    ExportPolicyUpdate,
    ExportRequestCreate,
    ExportRequestResponse,
)

router = APIRouter(prefix="/exports", tags=["controlled intelligence export"])


async def _policy(session: DatabaseSession, policy_id: UUID) -> TaxiiExportPolicy:
    policy = await session.get(TaxiiExportPolicy, policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export policy not found")
    return policy


async def _export(session: DatabaseSession, export_id: UUID) -> TaxiiExportRequest:
    item = await session.get(TaxiiExportRequest, export_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export request not found"
        )
    return item


async def _writable_collection(
    session: DatabaseSession, policy: TaxiiExportPolicy
) -> TaxiiCollection:
    collection = await session.get(TaxiiCollection, policy.collection_id)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The export destination collection no longer exists",
        )
    await session.refresh(collection, attribute_names=["server"])
    if not collection.server.enabled or not collection.can_write:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The TAXII relationship does not currently authorize collection writes",
        )
    return collection


@router.get("/policies", response_model=list[ExportPolicyResponse])
async def list_policies(
    session: DatabaseSession, user: AnalystUser
) -> list[TaxiiExportPolicy]:
    del user
    return list(
        (
            await session.scalars(
                select(TaxiiExportPolicy).order_by(TaxiiExportPolicy.created_at.desc())
            )
        ).all()
    )


@router.post(
    "/policies", response_model=ExportPolicyResponse, status_code=status.HTTP_201_CREATED
)
async def create_policy(
    payload: ExportPolicyCreate,
    session: DatabaseSession,
    user: AdminUser,
) -> TaxiiExportPolicy:
    duplicate = await session.scalar(
        select(TaxiiExportPolicy.id).where(
            (TaxiiExportPolicy.name == payload.name)
            | (TaxiiExportPolicy.collection_id == payload.collection_id)
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An export policy already uses this name or collection",
        )
    collection = await session.get(TaxiiCollection, payload.collection_id)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="TAXII collection not found"
        )
    await session.refresh(collection, attribute_names=["server"])
    if not collection.server.enabled or not collection.can_write:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export policies require an enabled, write-authorized TAXII collection",
        )
    policy = TaxiiExportPolicy(
        collection_id=collection.id,
        name=payload.name,
        enabled=False,
        allowed_marking_refs=sorted(payload.allowed_marking_refs),
        allow_unmarked=payload.allow_unmarked,
        max_objects=payload.max_objects,
        require_approval=True,
        created_by=user.id,
    )
    session.add(policy)
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="export.policy_created_disabled",
        object_type="taxii_export_policy",
        object_id=policy.id,
        details={
            "collection_id": str(collection.id),
            "allowed_marking_refs": policy.allowed_marking_refs,
            "allow_unmarked": policy.allow_unmarked,
        },
    )
    await session.commit()
    await session.refresh(policy)
    return policy


@router.put("/policies/{policy_id}", response_model=ExportPolicyResponse)
async def update_policy(
    policy_id: UUID,
    payload: ExportPolicyUpdate,
    session: DatabaseSession,
    user: AdminUser,
) -> TaxiiExportPolicy:
    policy = await _policy(session, policy_id)
    if payload.enabled:
        await _writable_collection(session, policy)
    policy.enabled = payload.enabled
    policy.allowed_marking_refs = sorted(payload.allowed_marking_refs)
    policy.allow_unmarked = payload.allow_unmarked
    policy.max_objects = payload.max_objects
    emit_audit(
        session,
        actor_id=user.id,
        action="export.policy_configuration_updated",
        object_type="taxii_export_policy",
        object_id=policy.id,
        details={
            "enabled": policy.enabled,
            "allowed_marking_refs": policy.allowed_marking_refs,
            "allow_unmarked": policy.allow_unmarked,
            "max_objects": policy.max_objects,
        },
    )
    await session.commit()
    await session.refresh(policy)
    return policy


@router.get("/eligible-evidence", response_model=list[EligibleExportEvidence])
async def eligible_evidence(
    policy_id: UUID,
    session: DatabaseSession,
    user: AnalystUser,
    limit: int = 200,
) -> list[EligibleExportEvidence]:
    del user
    policy = await _policy(session, policy_id)
    evidence = list(
        (
            await session.scalars(
                select(Evidence).order_by(Evidence.created_at.desc()).limit(min(max(limit, 1), 500))
            )
        ).all()
    )
    response: list[EligibleExportEvidence] = []
    for item in evidence:
        try:
            candidate = await export_candidate(session, item)
        except ExportValidationError:
            continue
        try:
            validate_candidate(candidate, policy)
            eligible = True
            reason = None
        except ExportValidationError as exc:
            eligible = False
            reason = str(exc)
        response.append(
            EligibleExportEvidence(
                evidence_id=item.id,
                entity_id=candidate.entity.id,
                entity_type=candidate.entity.entity_type.value,
                normalized_value=candidate.entity.normalized_value,
                claim=item.claim,
                polarity=item.polarity.value,
                marking_refs=candidate.marking_refs,
                eligible=eligible,
                reason=reason,
            )
        )
    return response


@router.post(
    "/requests", response_model=ExportRequestResponse, status_code=status.HTTP_201_CREATED
)
async def request_export(
    payload: ExportRequestCreate,
    session: DatabaseSession,
    user: AnalystUser,
) -> TaxiiExportRequest:
    policy = await _policy(session, payload.policy_id)
    if not policy.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Export policy is disabled"
        )
    await _writable_collection(session, policy)
    try:
        bundle, candidates = await build_export_bundle(session, policy, payload.evidence_ids)
    except ExportValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    now = datetime.now(UTC)
    approval = ApprovalRequest(
        action="TAXII_STIX_EXPORT",
        risk_summary=payload.risk_summary.strip(),
        status=ApprovalStatus.PENDING,
        requested_by=user.id,
    )
    session.add(approval)
    await session.flush()
    item = TaxiiExportRequest(
        policy_id=policy.id,
        approval_id=approval.id,
        requested_by=user.id,
        status=ExportStatus.PENDING_APPROVAL,
        evidence_ids=[str(candidate.evidence.id) for candidate in candidates],
        bundle_id=str(bundle["id"]),
        bundle_hash=bundle_hash(bundle),
        stix_bundle=bundle,
        object_count=len(candidates),
        requested_at=now,
    )
    session.add(item)
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="export.requested",
        object_type="taxii_export_request",
        object_id=item.id,
        details={
            "policy_id": str(policy.id),
            "approval_id": str(approval.id),
            "bundle_hash": item.bundle_hash,
            "object_count": item.object_count,
        },
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.post("/requests/{export_id}/resolve", response_model=ExportRequestResponse)
async def resolve_export(
    export_id: UUID,
    payload: ExportApprovalResolve,
    session: DatabaseSession,
    user: AdminUser,
) -> TaxiiExportRequest:
    item = await _export(session, export_id)
    if item.status != ExportStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Export is not pending")
    if item.requested_by == user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export approval requires a different administrator",
        )
    approval = await session.get(ApprovalRequest, item.approval_id)
    if approval is None or approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval is not pending")
    now = datetime.now(UTC)
    approval.status = payload.status
    approval.resolved_by = user.id
    approval.resolution_rationale = payload.rationale.strip()
    approval.resolved_at = now
    item.status = (
        ExportStatus.APPROVED
        if payload.status == ApprovalStatus.APPROVED
        else ExportStatus.REJECTED
    )
    item.approved_at = now if payload.status == ApprovalStatus.APPROVED else None
    emit_audit(
        session,
        actor_id=user.id,
        action="export.approval_resolved",
        object_type="taxii_export_request",
        object_id=item.id,
        details={"status": item.status.value, "bundle_hash": item.bundle_hash},
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.post("/requests/{export_id}/deliver", response_model=ExportRequestResponse)
async def deliver_export(
    export_id: UUID,
    request: Request,
    session: DatabaseSession,
    user: AnalystUser,
) -> TaxiiExportRequest:
    item = await _export(session, export_id)
    if item.status not in {ExportStatus.APPROVED, ExportStatus.FAILED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export requires approval and must not already be delivered",
        )
    approval = await session.get(ApprovalRequest, item.approval_id)
    if (
        approval is None
        or approval.status != ApprovalStatus.APPROVED
        or approval.resolved_by is None
        or approval.resolved_by == item.requested_by
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export requires approval from a different administrator",
        )
    policy = await _policy(session, item.policy_id)
    if not policy.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Export policy is disabled"
        )
    collection = await _writable_collection(session, policy)
    try:
        objects = validate_frozen_bundle(item.stix_bundle, item.bundle_hash, policy)
    except ExportValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    item.status = ExportStatus.DELIVERING
    item.delivery_attempts += 1
    item.error = None
    await session.commit()
    taxii_client: TaxiiClient = request.app.state.taxii_client
    try:
        receipt = await taxii_client.send_objects(collection.server, collection, objects)
        item.status = ExportStatus.DELIVERED
        item.delivery_receipt = receipt
        item.delivered_at = datetime.now(UTC)
        action = "export.delivered"
    except TaxiiError as exc:
        item.status = ExportStatus.FAILED
        item.error = str(exc)
        action = "export.delivery_failed"
    emit_audit(
        session,
        actor_id=user.id,
        action=action,
        object_type="taxii_export_request",
        object_id=item.id,
        details={
            "bundle_hash": item.bundle_hash,
            "attempt": item.delivery_attempts,
            "status": item.status.value,
        },
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/requests", response_model=list[ExportRequestResponse])
async def list_exports(
    session: DatabaseSession, user: AnalystUser, limit: int = 50
) -> list[TaxiiExportRequest]:
    del user
    return list(
        (
            await session.scalars(
                select(TaxiiExportRequest)
                .order_by(TaxiiExportRequest.requested_at.desc())
                .limit(min(max(limit, 1), 200))
            )
        ).all()
    )

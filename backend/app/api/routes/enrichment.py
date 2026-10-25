from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.dependencies import AdminUser, DatabaseSession
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.enrichment import run_enrichment_policy
from app.models import EnrichmentPolicy, EnrichmentRun
from app.operations.audit import emit_audit
from app.schemas.enrichment import (
    EnrichmentPolicyCreate,
    EnrichmentPolicyResponse,
    EnrichmentPolicyUpdate,
    EnrichmentRunResponse,
)

router = APIRouter(prefix="/enrichment", tags=["intelligence enrichment"])


async def _policy(session: DatabaseSession, policy_id: UUID) -> EnrichmentPolicy:
    policy = await session.get(EnrichmentPolicy, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Enrichment policy not found"
        )
    return policy


@router.get("/policies", response_model=list[EnrichmentPolicyResponse])
async def list_policies(
    session: DatabaseSession, user: AdminUser
) -> list[EnrichmentPolicy]:
    del user
    return list(
        (await session.scalars(select(EnrichmentPolicy).order_by(EnrichmentPolicy.name))).all()
    )


@router.post(
    "/policies", response_model=EnrichmentPolicyResponse, status_code=status.HTTP_201_CREATED
)
async def create_policy(
    payload: EnrichmentPolicyCreate,
    request: Request,
    session: DatabaseSession,
    user: AdminUser,
) -> EnrichmentPolicy:
    duplicate = await session.scalar(
        select(EnrichmentPolicy.id).where(EnrichmentPolicy.name == payload.name)
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An enrichment policy already uses this name",
        )
    manager: ConnectorManager = request.app.state.connector_manager
    connectors = {item.manifest.source_id: item for item in manager.registry.all()}
    unknown = sorted(set(payload.source_ids) - set(connectors))
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown or unavailable connector: {', '.join(unknown)}",
        )
    if "local-fixtures" in payload.source_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demonstration connectors cannot be used by automated enrichment",
        )
    selected_types = {value.value for value in payload.entity_types}
    unsupported = [
        source_id
        for source_id in payload.source_ids
        if not any(
            capability.operation == "lookup"
            and bool(capability.entity_types & selected_types)
            for capability in connectors[source_id].manifest.capabilities
        )
    ]
    if unsupported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Selected entity types are unsupported by: {', '.join(unsupported)}",
        )
    policy = EnrichmentPolicy(
        name=payload.name,
        entity_types=sorted(selected_types),
        source_ids=sorted(payload.source_ids),
        max_entities_per_run=payload.max_entities_per_run,
        cadence_minutes=payload.cadence_minutes,
        enabled=True,
        created_by=user.id,
        next_run_at=datetime.now(UTC),
    )
    session.add(policy)
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="enrichment.policy_created",
        object_type="enrichment_policy",
        object_id=policy.id,
        details={"entity_types": policy.entity_types, "source_ids": policy.source_ids},
    )
    await session.commit()
    await session.refresh(policy)
    return policy


@router.put("/policies/{policy_id}", response_model=EnrichmentPolicyResponse)
async def update_policy(
    policy_id: UUID,
    payload: EnrichmentPolicyUpdate,
    session: DatabaseSession,
    user: AdminUser,
) -> EnrichmentPolicy:
    policy = await _policy(session, policy_id)
    policy.enabled = payload.enabled
    policy.cadence_minutes = payload.cadence_minutes
    policy.next_run_at = datetime.now(UTC) if policy.enabled else None
    emit_audit(
        session,
        actor_id=user.id,
        action="enrichment.policy_configuration_updated",
        object_type="enrichment_policy",
        object_id=policy.id,
        details={"enabled": policy.enabled, "cadence_minutes": policy.cadence_minutes},
    )
    await session.commit()
    await session.refresh(policy)
    return policy


@router.post("/policies/{policy_id}/run", response_model=EnrichmentRunResponse)
async def run_policy(
    policy_id: UUID,
    request: Request,
    session: DatabaseSession,
    user: AdminUser,
) -> EnrichmentRunResponse:
    policy = await _policy(session, policy_id)
    if not policy.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Enrichment policy is paused"
        )
    manager: ConnectorManager = request.app.state.connector_manager
    run = await run_enrichment_policy(session, manager, policy, user.id)
    await session.refresh(run, attribute_names=["items"])
    return EnrichmentRunResponse.model_validate(run)


@router.get("/runs", response_model=list[EnrichmentRunResponse])
async def list_runs(
    session: DatabaseSession, user: AdminUser, limit: int = 50
) -> list[EnrichmentRunResponse]:
    del user
    bounded_limit = min(max(limit, 1), 200)
    runs = list(
        (
            await session.scalars(
                select(EnrichmentRun)
                .order_by(EnrichmentRun.started_at.desc())
                .limit(bounded_limit)
            )
        ).all()
    )
    return [EnrichmentRunResponse.model_validate(run) for run in runs]

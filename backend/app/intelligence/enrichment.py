from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.collection import collect_entity
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.normalization import normalize_entity
from app.models import (
    EnrichmentItem,
    EnrichmentPolicy,
    EnrichmentRun,
    Entity,
    Observation,
)
from app.models.enums import CollectionJobStatus, EntityType
from app.operations.audit import emit_audit


async def run_enrichment_policy(
    session: AsyncSession,
    manager: ConnectorManager,
    policy: EnrichmentPolicy,
    actor_id: UUID,
) -> EnrichmentRun:
    now = datetime.now(UTC)
    run = EnrichmentRun(
        policy_id=policy.id,
        triggered_by=actor_id,
        status=CollectionJobStatus.RUNNING,
        started_at=now,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    enriched_entities = (
        select(EnrichmentItem.entity_id)
        .join(EnrichmentRun, EnrichmentRun.id == EnrichmentItem.run_id)
        .where(EnrichmentRun.policy_id == policy.id)
    )
    entity_types = [EntityType(value) for value in policy.entity_types]
    candidates = list(
        (
            await session.scalars(
                select(Entity)
                .where(
                    Entity.entity_type.in_(entity_types),
                    Entity.id.not_in(enriched_entities),
                )
                .order_by(Entity.created_at, Entity.id)
                .limit(policy.max_entities_per_run)
            )
        ).all()
    )
    run.candidate_entities = len(candidates)
    outcomes: Counter[str] = Counter()
    item_statuses: list[CollectionJobStatus] = []
    new_observation_count = 0
    for entity in candidates:
        before = set(
            (
                await session.scalars(
                    select(Observation.id).where(Observation.entity_id == entity.id)
                )
            ).all()
        )
        normalized = normalize_entity(entity.normalized_value, entity.entity_type)
        _, job, results, observation_ids = await collect_entity(
            session, manager, normalized, set(policy.source_ids)
        )
        persisted_ids = sorted({str(item) for item in observation_ids.values()})
        new_ids = sorted(
            str(item) for item in observation_ids.values() if item not in before
        )
        source_outcomes = []
        for result in results:
            outcomes[result.outcome.value] += 1
            source_outcomes.append(
                {
                    "source_id": result.source_id,
                    "outcome": result.outcome.value,
                    "message": result.message,
                    "retry_after_seconds": result.retry_after_seconds,
                }
            )
        if not results:
            outcomes["NO_APPLICABLE_CONNECTOR"] += 1
            source_outcomes.append(
                {
                    "source_id": None,
                    "outcome": "NO_APPLICABLE_CONNECTOR",
                    "message": "No selected connector supports this entity type.",
                    "retry_after_seconds": None,
                }
            )
        item_statuses.append(job.status)
        new_observation_count += len(new_ids)
        session.add(
            EnrichmentItem(
                run_id=run.id,
                entity_id=entity.id,
                collection_job_id=job.id,
                status=job.status,
                source_outcomes=source_outcomes,
                observation_ids=persisted_ids,
                new_observation_ids=new_ids,
            )
        )

    run.processed_entities = len(candidates)
    run.new_observations = new_observation_count
    run.source_outcomes = dict(outcomes)
    if not item_statuses or all(
        status == CollectionJobStatus.COMPLETED for status in item_statuses
    ):
        run.status = CollectionJobStatus.COMPLETED
    elif any(status != CollectionJobStatus.FAILED for status in item_statuses):
        run.status = CollectionJobStatus.PARTIAL
    else:
        run.status = CollectionJobStatus.FAILED
    run.completed_at = datetime.now(UTC)
    policy.last_run_at = run.completed_at
    policy.next_run_at = run.completed_at + timedelta(minutes=policy.cadence_minutes)
    emit_audit(
        session,
        actor_id=actor_id,
        action="enrichment.policy_run_completed",
        object_type="enrichment_run",
        object_id=run.id,
        details={
            "policy_id": str(policy.id),
            "status": run.status.value,
            "processed_entities": run.processed_entities,
            "new_observations": run.new_observations,
            "source_outcomes": run.source_outcomes,
        },
    )
    await session.commit()
    await session.refresh(run)
    return run


async def run_due_enrichment_policies(
    session: AsyncSession, manager: ConnectorManager
) -> list[EnrichmentRun]:
    now = datetime.now(UTC)
    policies = list(
        (
            await session.scalars(
                select(EnrichmentPolicy)
                .where(
                    EnrichmentPolicy.enabled.is_(True),
                    EnrichmentPolicy.next_run_at <= now,
                )
                .order_by(EnrichmentPolicy.next_run_at)
                .limit(20)
            )
        ).all()
    )
    return [
        await run_enrichment_policy(session, manager, policy, policy.created_by)
        for policy in policies
    ]

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.collection import get_or_create_entity, observation_record_hash
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.connectors.models import ConnectorOutcome, ConnectorRequest
from app.intelligence.normalization import NormalizationError, normalize_entity
from app.models import (
    Entity,
    FeedRun,
    FeedRunItem,
    FeedSubscription,
    Observation,
    Source,
    SourceRecord,
)
from app.models.enums import CollectionJobStatus, EntityType, SourceHealth
from app.operations.audit import emit_audit

_HEALTHY_OUTCOMES = {ConnectorOutcome.SUCCESS, ConnectorOutcome.NO_RESULT}


async def run_feed_subscription(
    session: AsyncSession,
    manager: ConnectorManager,
    subscription: FeedSubscription,
    actor_id: UUID,
) -> FeedRun:
    started_at = datetime.now(UTC)
    run = FeedRun(
        subscription_id=subscription.id,
        triggered_by=actor_id,
        status=CollectionJobStatus.RUNNING,
        started_at=started_at,
    )
    session.add(run)
    await session.commit()

    results = await manager.fetch_feed(
        ConnectorRequest(limit=subscription.max_records),
        source_ids={subscription.source.source_id},
    )
    if not results:
        run.status = CollectionJobStatus.FAILED
        run.error = "The configured source does not expose a feed connector"
        run.completed_at = datetime.now(UTC)
        subscription.last_run_at = run.completed_at
        subscription.next_run_at = run.completed_at + timedelta(
            minutes=subscription.cadence_minutes
        )
        await session.commit()
        await session.refresh(run, attribute_names=["items"])
        return run

    result = results[0]
    run.connector_outcome = result.outcome.value
    run.received_records = len(result.observations) + len(result.issues)
    source = await session.get(Source, subscription.source_id)
    checked_at = datetime.now(UTC)
    if source is None:
        run.status = CollectionJobStatus.FAILED
        run.error = "The configured source catalog record no longer exists"
    else:
        source.last_checked = checked_at
        if result.outcome in _HEALTHY_OUTCOMES:
            source.health_status = SourceHealth.HEALTHY
            source.last_success = checked_at
            source.last_error = None
        elif result.outcome == ConnectorOutcome.NOT_CONFIGURED:
            source.health_status = SourceHealth.NOT_CONFIGURED
            source.last_error = result.message or result.outcome.value
        else:
            source.health_status = SourceHealth.DEGRADED
            source.last_error = result.message or result.outcome.value

    if source is not None and result.outcome == ConnectorOutcome.SUCCESS:
        for index, observation in enumerate(result.observations):
            raw_record = observation.raw_record or observation.attributes
            try:
                entity_type = EntityType(observation.entity.entity_type)
                normalized = normalize_entity(observation.entity.value, entity_type)
                existing = await session.scalar(
                    select(Entity.id).where(
                        Entity.entity_type == normalized.entity_type,
                        Entity.normalized_value == normalized.normalized_value,
                    )
                )
                entity = await get_or_create_entity(session, normalized)
                if existing is None:
                    run.created_entities += 1
                else:
                    run.reused_entities += 1
                content_hash = observation_record_hash(observation)
                source_record = await session.scalar(
                    select(SourceRecord).where(
                        SourceRecord.source_id == source.id,
                        SourceRecord.entity_id == entity.id,
                        SourceRecord.content_hash == content_hash,
                    )
                )
                if source_record is None:
                    source_record = SourceRecord(
                        source_id=source.id,
                        entity_id=entity.id,
                        external_id=observation.external_id,
                        source_reference=observation.source_reference or result.raw_reference,
                        published_at=observation.observed_at,
                        retrieved_at=checked_at,
                        content_hash=content_hash,
                        raw_record=raw_record,
                    )
                    session.add(source_record)
                    await session.flush()
                persisted = await session.scalar(
                    select(Observation).where(
                        Observation.source_record_id == source_record.id,
                        Observation.observation_type == observation.observation_type,
                    )
                )
                if persisted is None:
                    persisted = Observation(
                        entity_id=entity.id,
                        source_id=source.id,
                        source_record_id=source_record.id,
                        observation_type=observation.observation_type,
                        summary=observation.summary,
                        observed_at=observation.observed_at,
                        source_reference=observation.source_reference,
                        upstream_provenance=result.raw_reference,
                        raw_record=observation.attributes,
                    )
                    session.add(persisted)
                    await session.flush()
                    disposition = "IMPORTED"
                    code = "OBSERVATION_CREATED"
                    run.new_observations += 1
                else:
                    disposition = "DEDUPLICATED"
                    code = "OBSERVATION_REUSED"
                    run.deduplicated_observations += 1
                run.accepted_records += 1
                session.add(
                    FeedRunItem(
                        run_id=run.id,
                        record_index=index,
                        external_id=observation.external_id,
                        disposition=disposition,
                        code=code,
                        message=(
                            "New canonical observation recorded"
                            if disposition == "IMPORTED"
                            else "Matching source record and observation already exist"
                        ),
                        entity_id=entity.id,
                        observation_id=persisted.id,
                        source_record_id=source_record.id,
                        content_hash=content_hash,
                        raw_record=raw_record,
                    )
                )
            except (NormalizationError, ValueError, TypeError) as exc:
                run.rejected_records += 1
                session.add(
                    FeedRunItem(
                        run_id=run.id,
                        record_index=index,
                        external_id=observation.external_id,
                        disposition="REJECTED",
                        code="NORMALIZATION_FAILED",
                        message=str(exc),
                        raw_record=raw_record,
                    )
                )
        issue_offset = len(result.observations)
        for offset, issue in enumerate(result.issues):
            run.rejected_records += 1
            session.add(
                FeedRunItem(
                    run_id=run.id,
                    record_index=issue_offset + offset,
                    external_id=issue.external_id,
                    disposition="REJECTED",
                    code=issue.code,
                    message=issue.message,
                    raw_record=issue.raw_record,
                )
            )
        run.status = (
            CollectionJobStatus.PARTIAL
            if run.rejected_records
            else CollectionJobStatus.COMPLETED
        )
    elif result.outcome == ConnectorOutcome.NO_RESULT:
        run.status = CollectionJobStatus.COMPLETED
    else:
        run.status = CollectionJobStatus.FAILED
        run.error = result.message or result.outcome.value

    run.completed_at = datetime.now(UTC)
    subscription.last_run_at = run.completed_at
    subscription.next_run_at = run.completed_at + timedelta(minutes=subscription.cadence_minutes)
    emit_audit(
        session,
        actor_id=actor_id,
        action="feed.subscription_run_completed",
        object_type="feed_run",
        object_id=run.id,
        details={
            "source_id": subscription.source.source_id,
            "status": run.status.value,
            "accepted_records": run.accepted_records,
            "rejected_records": run.rejected_records,
        },
    )
    await session.commit()
    await session.refresh(run, attribute_names=["items"])
    return run


async def run_due_feed_subscriptions(
    session: AsyncSession, manager: ConnectorManager
) -> int:
    now = datetime.now(UTC)
    subscriptions = list(
        (
            await session.scalars(
                select(FeedSubscription).where(
                    FeedSubscription.enabled.is_(True),
                    FeedSubscription.next_run_at.is_not(None),
                    FeedSubscription.next_run_at <= now,
                )
            )
        ).all()
    )
    for subscription in subscriptions:
        await run_feed_subscription(session, manager, subscription, subscription.created_by)
    return len(subscriptions)

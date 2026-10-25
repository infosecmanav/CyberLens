import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.connectors.models import (
    ConnectorOutcome,
    ConnectorRequest,
    ConnectorResult,
    IntelligenceEntity,
    NormalizedObservation,
)
from app.intelligence.normalization import NormalizedEntity
from app.models import CollectionJob, Entity, Observation, Source, SourceRecord
from app.models.enums import CollectionJobStatus, SourceHealth

_HEALTHY_OUTCOMES = {ConnectorOutcome.SUCCESS, ConnectorOutcome.NO_RESULT}


async def get_or_create_entity(session: AsyncSession, normalized: NormalizedEntity) -> Entity:
    entity = await session.scalar(
        select(Entity).where(
            Entity.entity_type == normalized.entity_type,
            Entity.normalized_value == normalized.normalized_value,
        )
    )
    if entity is not None:
        return entity
    entity = Entity(
        entity_type=normalized.entity_type,
        value=normalized.original_value.strip(),
        normalized_value=normalized.normalized_value,
        display_name=normalized.normalized_value,
        attributes=normalized.attributes,
    )
    session.add(entity)
    await session.flush()
    return entity


def observation_record_hash(observation: NormalizedObservation) -> str:
    record = observation.raw_record or {
        "entity": observation.entity.model_dump(mode="json"),
        "observation_type": observation.observation_type,
        "summary": observation.summary,
        "observed_at": observation.observed_at.isoformat(),
        "attributes": observation.attributes,
    }
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _job_status(results: list[ConnectorResult]) -> CollectionJobStatus:
    if not results or all(result.outcome in _HEALTHY_OUTCOMES for result in results):
        return CollectionJobStatus.COMPLETED
    if any(result.outcome in _HEALTHY_OUTCOMES for result in results):
        return CollectionJobStatus.PARTIAL
    return CollectionJobStatus.FAILED


async def collect_entity(
    session: AsyncSession,
    manager: ConnectorManager,
    normalized: NormalizedEntity,
    source_ids: set[str] | None,
) -> tuple[Entity, CollectionJob, list[ConnectorResult], dict[tuple[str, int], UUID]]:
    entity = await get_or_create_entity(session, normalized)
    request = ConnectorRequest(
        entity=IntelligenceEntity(
            entity_type=normalized.entity_type.value,
            value=normalized.normalized_value,
        )
    )
    applicable = manager.registry.applicable("lookup", normalized.entity_type.value)
    requested = sorted(
        connector.manifest.source_id
        for connector in applicable
        if source_ids is None or connector.manifest.source_id in source_ids
    )
    now = datetime.now(UTC)
    job = CollectionJob(
        entity_id=entity.id,
        status=CollectionJobStatus.RUNNING,
        requested_source_ids=requested,
        started_at=now,
    )
    session.add(job)
    await session.commit()

    results = await manager.lookup(request, source_ids=source_ids)
    source_slugs = {result.source_id for result in results}
    sources = {
        source.source_id: source
        for source in (
            await session.scalars(select(Source).where(Source.source_id.in_(source_slugs)))
        ).all()
    }
    observation_ids: dict[tuple[str, int], UUID] = {}
    checked_at = datetime.now(UTC)
    for result in results:
        source = sources.get(result.source_id)
        if source is None:
            continue
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

        for index, observation in enumerate(result.observations):
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
                    raw_record=observation.raw_record or observation.attributes,
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
            observation_ids[(result.source_id, index)] = persisted.id

    job.status = _job_status(results)
    job.completed_at = datetime.now(UTC)
    job.outcome_summary = dict(Counter(result.outcome.value for result in results))
    if not results:
        job.outcome_summary = {"NO_APPLICABLE_CONNECTOR": 1}
    await session.commit()
    await session.refresh(entity)
    await session.refresh(job)
    return entity, job, results, observation_ids

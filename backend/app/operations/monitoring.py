import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.collection import collect_entity
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.normalization import normalize_entity
from app.models import (
    Entity,
    EntityRelationship,
    IntelligenceChange,
    MonitoringObjective,
    MonitoringRun,
    Observation,
)
from app.models.enums import (
    IntelligenceChangeType,
    MonitoringRunStatus,
    MonitoringStatus,
)


async def run_monitoring_objective(
    session: AsyncSession,
    manager: ConnectorManager,
    objective: MonitoringObjective,
) -> MonitoringRun:
    now = datetime.now(UTC)
    run = MonitoringRun(
        objective_id=objective.id,
        status=MonitoringRunStatus.RUNNING,
        started_at=now,
        change_summary={},
    )
    session.add(run)
    await session.commit()
    try:
        if objective.entity_id is not None:
            entity = await session.get(Entity, objective.entity_id)
            if entity is not None:
                normalized = normalize_entity(entity.normalized_value, entity.entity_type)
                public_sources = {
                    connector.manifest.source_id
                    for connector in manager.registry.all()
                    if connector.manifest.source_id != "local-fixtures"
                }
                await collect_entity(session, manager, normalized, public_sources)
        observations = []
        relationships = []
        if objective.entity_id is not None:
            observations = list(
                (
                    await session.scalars(
                        select(Observation).where(Observation.entity_id == objective.entity_id)
                    )
                ).all()
            )
            relationships = list(
                (
                    await session.scalars(
                        select(EntityRelationship).where(
                            or_(
                                EntityRelationship.source_entity_id == objective.entity_id,
                                EntityRelationship.target_entity_id == objective.entity_id,
                            )
                        )
                    )
                ).all()
            )
        payload = {
            "observation_ids": sorted(str(item.id) for item in observations),
            "relationship_ids": sorted(str(item.id) for item in relationships),
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        previous_run = await session.scalar(
            select(MonitoringRun)
            .where(
                MonitoringRun.objective_id == objective.id,
                MonitoringRun.id != run.id,
                MonitoringRun.status == MonitoringRunStatus.COMPLETED,
            )
            .order_by(MonitoringRun.completed_at.desc())
        )
        current_counts = {
            "observations": len(observations),
            "relationships": len(relationships),
        }
        if objective.last_fingerprint is None:
            change_type = IntelligenceChangeType.BASELINE
            summary = "Monitoring baseline recorded."
            actionable = False
        elif objective.last_fingerprint == fingerprint:
            change_type = IntelligenceChangeType.NO_MATERIAL_CHANGE
            summary = "No material intelligence change was detected."
            actionable = False
        else:
            previous_counts = previous_run.change_summary if previous_run else {}
            if len(observations) > int(previous_counts.get("observations", 0)):
                change_type = IntelligenceChangeType.NEW_OBSERVATION
                summary = "New source-backed observations were detected."
            else:
                change_type = IntelligenceChangeType.NEW_RELATIONSHIP
                summary = "New evidence-backed relationships were detected."
            actionable = True
        run.status = MonitoringRunStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        run.fingerprint = fingerprint
        run.change_summary = current_counts
        objective.last_fingerprint = fingerprint
        objective.last_run_at = run.completed_at
        objective.next_run_at = run.completed_at + timedelta(minutes=objective.cadence_minutes)
        session.add(
            IntelligenceChange(
                objective_id=objective.id,
                run_id=run.id,
                change_type=change_type,
                entity_id=objective.entity_id,
                summary=summary,
                details=current_counts,
                is_actionable=actionable,
            )
        )
        await session.commit()
    except Exception as exc:
        run.status = MonitoringRunStatus.FAILED
        run.completed_at = datetime.now(UTC)
        run.error = str(exc)
        objective.last_run_at = run.completed_at
        objective.next_run_at = run.completed_at + timedelta(minutes=objective.cadence_minutes)
        await session.commit()
    await session.refresh(run)
    return run


async def run_due_objectives(
    session: AsyncSession, manager: ConnectorManager
) -> list[MonitoringRun]:
    now = datetime.now(UTC)
    objectives = list(
        (
            await session.scalars(
                select(MonitoringObjective).where(
                    MonitoringObjective.status == MonitoringStatus.ACTIVE,
                    or_(
                        MonitoringObjective.next_run_at.is_(None),
                        MonitoringObjective.next_run_at <= now,
                    ),
                )
            )
        ).all()
    )
    runs = []
    for objective in objectives:
        runs.append(await run_monitoring_objective(session, manager, objective))
    return runs

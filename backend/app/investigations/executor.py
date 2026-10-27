import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.collection import collect_entity, get_or_create_entity
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.connectors.models import ConnectorOutcome
from app.intelligence.normalization import normalize_entity
from app.investigations.cross_validation import (
    EvidenceSignal,
    classify_evidence_dimension,
    reconcile_evidence,
)
from app.models import (
    Assessment,
    AssessmentEvidence,
    Entity,
    EntityRelationship,
    Evidence,
    Finding,
    FindingEvidence,
    Investigation,
    InvestigationEntity,
    InvestigationEvent,
    InvestigationStep,
    Observation,
    Source,
)
from app.models.enums import (
    EntityType,
    EvidencePolarity,
    InvestigationStatus,
    InvestigationVerdict,
    StepStatus,
)


def _event(
    session: AsyncSession,
    investigation: Investigation,
    event_type: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        InvestigationEvent(
            investigation_id=investigation.id,
            occurred_at=datetime.now(UTC),
            event_type=event_type,
            message=message,
            details=details or {},
        )
    )


async def _observations(session: AsyncSession, entity_id: object) -> list[Observation]:
    return list(
        (
            await session.scalars(
                select(Observation)
                .where(Observation.entity_id == entity_id)
                .order_by(Observation.observed_at.desc())
            )
        ).all()
    )


async def _collect(
    session: AsyncSession,
    manager: ConnectorManager,
    investigation: Investigation,
) -> dict[str, Any]:
    if investigation.seed_entity_id is None:
        return {"skipped": True, "reason": "No seed entity was supplied"}
    entity = await session.get(Entity, investigation.seed_entity_id)
    if entity is None:
        return {"skipped": True, "reason": "Seed entity is no longer available"}
    request_budget = int(investigation.budgets.get("api_requests", 0))
    if request_budget == 0:
        raise BudgetExhausted("API request budget is zero")
    configured_sources = investigation.input_context.get("source_ids")
    source_ids = set(configured_sources) if isinstance(configured_sources, list) else None
    if source_ids is None and not investigation.input_context.get("include_demo", False):
        source_ids = {
            connector.manifest.source_id
            for connector in manager.registry.all()
            if connector.manifest.source_id != "local-fixtures"
        }
    applicable = manager.registry.applicable("lookup", entity.entity_type.value)
    selected = [
        connector
        for connector in applicable
        if source_ids is None or connector.manifest.source_id in source_ids
    ][:request_budget]
    bounded_sources = {connector.manifest.source_id for connector in selected}
    normalized = normalize_entity(entity.normalized_value, entity.entity_type)
    _, job, results, _ = await collect_entity(session, manager, normalized, bounded_sources)
    usage = dict(investigation.budget_usage)
    usage["api_requests"] = int(usage.get("api_requests", 0)) + len(results)
    investigation.budget_usage = usage
    limitations = list(investigation.limitations)
    for result in results:
        if result.outcome not in {ConnectorOutcome.SUCCESS, ConnectorOutcome.NO_RESULT}:
            limitations.append(f"{result.source_id}: {result.outcome.value}")
    investigation.limitations = sorted(set(limitations))
    await session.commit()
    return {
        "collection_job_id": str(job.id),
        "outcomes": {result.source_id: result.outcome.value for result in results},
        "requests_used": len(results),
    }


async def _validate(session: AsyncSession, investigation: Investigation) -> dict[str, Any]:
    if investigation.seed_entity_id is None:
        return {"evidence_created": 0, "reason": "No seed entity"}
    observations = await _observations(session, investigation.seed_entity_id)
    evidence_ids: list[str] = []
    for observation in observations:
        assessment_dimension = classify_evidence_dimension(observation.observation_type)
        polarity = (
            EvidencePolarity.SUPPORTS
            if observation.observation_type == "KNOWN_EXPLOITED_VULNERABILITY"
            else (
                EvidencePolarity.CONFLICTS
                if observation.observation_type == "BENIGN_CLASSIFICATION"
                else EvidencePolarity.CONTEXTUAL
            )
        )
        claim = observation.summary
        evidence = await session.scalar(
            select(Evidence).where(
                Evidence.observation_id == observation.id,
                Evidence.claim == claim,
            )
        )
        if evidence is None:
            evidence = Evidence(
                observation_id=observation.id,
                polarity=polarity,
                assessment_dimension=assessment_dimension,
                claim=claim,
                uncertainty_notes=(
                    "Demonstration data cannot support a real-world threat conclusion."
                    if observation.observation_type == "DEMONSTRATION_ONLY"
                    else (
                        "A provider's benign classification conflicts with threat evidence but "
                        "does not establish that the entity is safe."
                        if polarity == EvidencePolarity.CONFLICTS
                        else "Provider presence is scoped to the provider's published record."
                    )
                ),
            )
            session.add(evidence)
            await session.flush()
        elif evidence.promoted_by is None:
            evidence.assessment_dimension = assessment_dimension
        evidence_ids.append(str(evidence.id))
    return {"evidence_created": len(evidence_ids), "evidence_ids": evidence_ids}


async def _correlate(session: AsyncSession, investigation: Investigation) -> dict[str, Any]:
    if investigation.seed_entity_id is None:
        return {"relationships_created": 0, "reason": "No seed entity"}
    observations = await _observations(session, investigation.seed_entity_id)
    created = 0
    for observation in observations:
        product = observation.raw_record.get("product")
        if not isinstance(product, str) or not product.strip():
            continue
        normalized = normalize_entity(product, EntityType.PRODUCT)
        related = await get_or_create_entity(session, normalized)
        link = await session.scalar(
            select(InvestigationEntity).where(
                InvestigationEntity.investigation_id == investigation.id,
                InvestigationEntity.entity_id == related.id,
                InvestigationEntity.role == "RELATED",
            )
        )
        if link is None:
            session.add(
                InvestigationEntity(
                    investigation_id=investigation.id,
                    entity_id=related.id,
                    role="RELATED",
                )
            )
        evidence = await session.scalar(
            select(Evidence).where(Evidence.observation_id == observation.id)
        )
        relationship = await session.scalar(
            select(EntityRelationship).where(
                EntityRelationship.source_entity_id == investigation.seed_entity_id,
                EntityRelationship.target_entity_id == related.id,
                EntityRelationship.relationship_type == "AFFECTS_PRODUCT",
            )
        )
        if relationship is None:
            session.add(
                EntityRelationship(
                    source_entity_id=investigation.seed_entity_id,
                    target_entity_id=related.id,
                    relationship_type="AFFECTS_PRODUCT",
                    evidence_id=evidence.id if evidence else None,
                    first_seen=observation.observed_at,
                    last_seen=observation.observed_at,
                    confidence=0.8,
                    provenance={
                        "source_reference": observation.source_reference,
                        "observation_id": str(observation.id),
                    },
                    uncertainty_notes=(
                        "The relationship reflects the named affected product in one source record."
                    ),
                )
            )
            created += 1
    return {"relationships_created": created}


def _summary_count(summary: dict[str, object], key: str) -> int:
    value = summary.get(key)
    return value if isinstance(value, int) else 0


def _dimensions(
    has_kev: bool, reconciliation: dict[str, object]
) -> dict[str, dict[str, str]]:
    provider_count = _summary_count(reconciliation, "provider_count")
    provenance_groups = _summary_count(reconciliation, "provenance_group_count")
    corroborating_groups = _summary_count(
        reconciliation, "supporting_provenance_groups"
    )
    return {
        "maliciousness": {
            "level": "NOT_ASSESSED",
            "rationale": "Object type alone does not establish maliciousness.",
        },
        "infrastructure_association": {
            "level": "NOT_ASSESSED",
            "rationale": "No infrastructure association was inferred.",
        },
        "malware_association": {
            "level": "NOT_ASSESSED",
            "rationale": "No malware association was inferred.",
        },
        "behavioral_association": {
            "level": "HIGH" if has_kev else "UNKNOWN",
            "rationale": (
                "CISA records known exploitation."
                if has_kev
                else "No verified behavioral observation was collected."
            ),
        },
        "threat_actor_attribution": {
            "level": "NOT_ASSESSED",
            "rationale": "No actor attribution is supported.",
        },
        "detection_applicability": {
            "level": "MEDIUM" if has_kev else "UNKNOWN",
            "rationale": (
                "Exploitation evidence warrants telemetry review."
                if has_kev
                else "Behavioral telemetry requirements are not established."
            ),
        },
        "independent_sources": {
            "level": str(corroborating_groups),
            "rationale": (
                f"{provider_count} direct provider(s) resolve to {provenance_groups} distinct "
                f"provenance group(s); the strongest aligned analytical dimension has "
                f"{corroborating_groups} supporting group(s)."
            ),
        },
    }


async def _assess(session: AsyncSession, investigation: Investigation) -> dict[str, Any]:
    observations = (
        await _observations(session, investigation.seed_entity_id)
        if investigation.seed_entity_id is not None
        else []
    )
    has_kev = any(
        observation.observation_type == "KNOWN_EXPLOITED_VULNERABILITY"
        for observation in observations
    )
    evidence_rows = (
        await session.execute(
            select(Evidence, Observation, Source.source_id)
            .join(Observation, Observation.id == Evidence.observation_id)
            .join(Source, Source.id == Observation.source_id)
            .where(Observation.entity_id == investigation.seed_entity_id)
        )
    ).all() if investigation.seed_entity_id is not None else []
    evidence = [item for item, _observation, _source_id in evidence_rows]
    reconciliation = reconcile_evidence(
        [
            EvidenceSignal(
                evidence_id=str(item.id),
                observation_id=str(observation.id),
                source_id=source_id,
                polarity=item.polarity,
                assessment_dimension=item.assessment_dimension,
                source_reference=observation.source_reference,
                upstream_provenance=observation.upstream_provenance,
                source_record_id=(
                    str(observation.source_record_id)
                    if observation.source_record_id is not None
                    else None
                ),
            )
            for item, observation, source_id in evidence_rows
        ]
    )
    verdict = InvestigationVerdict.SUSPICIOUS if has_kev else InvestigationVerdict.UNKNOWN
    dimensions = _dimensions(has_kev, reconciliation)
    assessment = await session.scalar(
        select(Assessment).where(Assessment.investigation_id == investigation.id)
    )
    base_rationale = (
        "Known exploitation is documented; asset exposure and local telemetry still require review."
        if has_kev
        else "Available evidence does not support a stronger conclusion."
    )
    reconciliation_status = str(reconciliation["status"])
    rationale = f"{base_rationale} {reconciliation['summary']}"
    raw_reconciliation_limitations = reconciliation.get("limitations")
    reconciliation_limitations = (
        [str(item) for item in raw_reconciliation_limitations]
        if isinstance(raw_reconciliation_limitations, list)
        else []
    )
    if assessment is None:
        assessment = Assessment(
            investigation_id=investigation.id,
            entity_id=investigation.seed_entity_id,
            assessment_type="THREAT_ASSESSMENT",
        )
        session.add(assessment)
    assessment.verdict = verdict
    assessment.confidence_dimensions = dimensions
    assessment.evidence_reconciliation = reconciliation
    assessment.methodology = "HEURISTIC_V3_DIMENSION_ALIGNED_UNCALIBRATED"
    assessment.rationale = rationale
    assessment.limitations = sorted(
        set([*investigation.limitations, *reconciliation_limitations])
    )
    await session.flush()
    for item in evidence:
        existing = await session.scalar(
            select(AssessmentEvidence).where(
                AssessmentEvidence.assessment_id == assessment.id,
                AssessmentEvidence.evidence_id == item.id,
            )
        )
        if existing is None:
            session.add(
                AssessmentEvidence(
                    assessment_id=assessment.id,
                    evidence_id=item.id,
                    polarity=item.polarity.value,
                )
            )
    finding = await session.scalar(
        select(Finding).where(Finding.investigation_id == investigation.id)
    )
    if finding is None:
        finding = Finding(
            investigation_id=investigation.id,
        )
        session.add(finding)
    finding.title = (
        "Known exploitation evidence" if has_kev else "Collection limitations recorded"
    )
    finding.statement = rationale
    finding.severity = "HIGH" if has_kev else "INFO"
    finding.confidence_dimensions = dimensions
    if reconciliation_status == "CONFLICTING_EVIDENCE":
        finding.uncertainty = (
            "Source-backed conflict remains unresolved; no automatic benign or malicious "
            "conclusion is made."
        )
    elif reconciliation_status == "SHARED_UPSTREAM_REPORTING":
        finding.uncertainty = (
            "Multiple provider records trace to shared upstream reporting and count as one "
            "provenance group."
        )
    else:
        finding.uncertainty = (
            "Known exploitation does not prove compromise of any particular environment."
            if has_kev
            else "No-result and unavailable sources cannot be interpreted as benign evidence."
        )
    await session.flush()
    for item in evidence:
        linked = await session.scalar(
            select(FindingEvidence).where(
                FindingEvidence.finding_id == finding.id,
                FindingEvidence.evidence_id == item.id,
            )
        )
        if linked is None:
            session.add(
                FindingEvidence(
                    finding_id=finding.id,
                    evidence_id=item.id,
                    dimension="behavioral_association",
                    rationale="The finding cites this source-backed observation.",
                )
            )
    investigation.verdict = verdict
    return {
        "assessment_id": str(assessment.id),
        "finding_id": str(finding.id),
        "verdict": verdict.value,
        "cross_validation_status": reconciliation_status,
        "provenance_groups": _summary_count(reconciliation, "provenance_group_count"),
    }


async def _detection_readiness(
    session: AsyncSession, investigation: Investigation
) -> dict[str, Any]:
    supporting = 0
    if investigation.seed_entity_id is not None:
        supporting = int(
            await session.scalar(
                select(Evidence)
                .join(Observation, Observation.id == Evidence.observation_id)
                .where(
                    Observation.entity_id == investigation.seed_entity_id,
                    Evidence.polarity == EvidencePolarity.SUPPORTS,
                )
                .with_only_columns(Evidence.id)
            )
            is not None
        )
    return {
        "eligible_for_draft": supporting > 0,
        "supporting_evidence_present": supporting > 0,
        "note": (
            "Any generated detection remains unvalidated until validation evidence is recorded."
        ),
    }


async def reconcile_investigation_evidence(
    session: AsyncSession, investigation: Investigation
) -> dict[str, Any]:
    validation = await _validate(session, investigation)
    assessment = await _assess(session, investigation)
    details = {
        **assessment,
        "evidence_created": validation.get("evidence_created", 0),
    }
    _event(
        session,
        investigation,
        "EVIDENCE_RECONCILED",
        "Evidence was reconciled across provider and upstream provenance groups.",
        details,
    )
    await session.commit()
    return details


class BudgetExhausted(RuntimeError):
    pass


async def run_investigation(
    session: AsyncSession,
    manager: ConnectorManager,
    investigation: Investigation,
) -> Investigation:
    if investigation.status == InvestigationStatus.COMPLETED:
        return investigation
    if investigation.status == InvestigationStatus.CANCELLED:
        return investigation
    steps = list(
        (
            await session.scalars(
                select(InvestigationStep)
                .where(InvestigationStep.investigation_id == investigation.id)
                .order_by(InvestigationStep.sequence)
            )
        ).all()
    )
    started = time.monotonic()
    if investigation.started_at is None:
        investigation.started_at = datetime.now(UTC)
    _event(session, investigation, "RUN_STARTED", "Investigation execution started.")
    await session.commit()
    handlers = {
        "collect": lambda: _collect(session, manager, investigation),
        "validate": lambda: _validate(session, investigation),
        "correlate": lambda: _correlate(session, investigation),
        "assess": lambda: _assess(session, investigation),
        "detection-readiness": lambda: _detection_readiness(session, investigation),
    }
    for step in steps:
        if step.status in {StepStatus.COMPLETED, StepStatus.SKIPPED}:
            continue
        runtime_budget = int(investigation.budgets.get("runtime_seconds", 60))
        if time.monotonic() - started >= runtime_budget:
            investigation.status = InvestigationStatus.WAITING_FOR_ANALYST
            investigation.limitations = sorted(
                set([*investigation.limitations, "Runtime budget exhausted"])
            )
            _event(session, investigation, "BUDGET_STOP", "Runtime budget exhausted.")
            await session.commit()
            return investigation
        investigation.status = step.phase
        step.status = StepStatus.RUNNING
        step.attempts += 1
        step.started_at = datetime.now(UTC)
        await session.commit()
        try:
            output = await handlers[step.idempotency_key]()
            step.output_data = output
            step.status = StepStatus.SKIPPED if output.get("skipped") else StepStatus.COMPLETED
            step.completed_at = datetime.now(UTC)
            _event(
                session,
                investigation,
                "STEP_COMPLETED",
                f"{step.title} finished with status {step.status.value}.",
                {"step_id": str(step.id)},
            )
            await session.commit()
        except BudgetExhausted as exc:
            step.status = StepStatus.SKIPPED
            step.error = str(exc)
            step.completed_at = datetime.now(UTC)
            investigation.status = InvestigationStatus.WAITING_FOR_ANALYST
            investigation.limitations = sorted(set([*investigation.limitations, str(exc)]))
            _event(session, investigation, "BUDGET_STOP", str(exc))
            await session.commit()
            return investigation
        except Exception as exc:
            step.status = StepStatus.FAILED
            step.error = str(exc)
            step.completed_at = datetime.now(UTC)
            investigation.status = InvestigationStatus.FAILED
            investigation.error = f"Step {step.idempotency_key} failed"
            _event(
                session,
                investigation,
                "RUN_FAILED",
                investigation.error,
                {"step_id": str(step.id)},
            )
            await session.commit()
            return investigation
    investigation.status = InvestigationStatus.COMPLETED
    investigation.completed_at = datetime.now(UTC)
    usage = dict(investigation.budget_usage)
    usage["runtime_seconds"] = round(time.monotonic() - started, 3)
    usage["cost_usd"] = 0.0
    investigation.budget_usage = usage
    _event(
        session,
        investigation,
        "RUN_COMPLETED",
        "Investigation completed with recorded limitations.",
        {"verdict": investigation.verdict.value if investigation.verdict else None},
    )
    await session.commit()
    return investigation

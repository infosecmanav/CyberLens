import hashlib
import json
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    Evidence,
    ImportObjectOutcome,
    Observation,
    SourceRecord,
    TaxiiExportPolicy,
)


class ExportValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ExportEvidenceCandidate:
    evidence: Evidence
    entity: Entity
    stix_object: dict[str, object]
    marking_refs: list[str]


def _marking_refs(record: dict[str, object]) -> list[str]:
    raw = record.get("object_marking_refs", [])
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str)][:100]


async def export_candidate(
    session: AsyncSession, evidence: Evidence
) -> ExportEvidenceCandidate:
    observation = await session.get(Observation, evidence.observation_id)
    if observation is None or observation.source_record_id is None:
        raise ExportValidationError("Evidence has no exportable source record")
    source_record = await session.get(SourceRecord, observation.source_record_id)
    entity = await session.get(Entity, observation.entity_id)
    if source_record is None or entity is None:
        raise ExportValidationError("Evidence lineage is incomplete")
    record = source_record.raw_record
    if (
        not isinstance(record, dict)
        or record.get("type") != "indicator"
        or record.get("spec_version") != "2.1"
        or not isinstance(record.get("id"), str)
    ):
        raise ExportValidationError("Evidence does not originate from a STIX 2.1 Indicator")
    return ExportEvidenceCandidate(
        evidence=evidence,
        entity=entity,
        stix_object=record,
        marking_refs=_marking_refs(record),
    )


def validate_candidate(candidate: ExportEvidenceCandidate, policy: TaxiiExportPolicy) -> None:
    if candidate.evidence.analyst_reviewed_at is None or candidate.evidence.promoted_by is None:
        raise ExportValidationError("Every export object requires analyst-reviewed evidence")
    if not candidate.marking_refs:
        if not policy.allow_unmarked:
            raise ExportValidationError("Unmarked STIX objects are not allowed by this policy")
        return
    blocked = sorted(set(candidate.marking_refs) - set(policy.allowed_marking_refs))
    if blocked:
        raise ExportValidationError(
            f"STIX object contains markings outside the destination allowlist: {', '.join(blocked)}"
        )


async def build_export_bundle(
    session: AsyncSession,
    policy: TaxiiExportPolicy,
    evidence_ids: list[UUID],
) -> tuple[dict[str, object], list[ExportEvidenceCandidate]]:
    if len(evidence_ids) > policy.max_objects:
        raise ExportValidationError("Export exceeds the policy object budget")
    evidence = list(
        (
            await session.scalars(
                select(Evidence).where(Evidence.id.in_(set(evidence_ids)))
            )
        ).all()
    )
    by_id = {item.id: item for item in evidence}
    if set(by_id) != set(evidence_ids):
        raise ExportValidationError("One or more evidence records do not exist")
    candidates = [await export_candidate(session, by_id[item]) for item in evidence_ids]
    for candidate in candidates:
        validate_candidate(candidate, policy)

    marking_ids = sorted({item for candidate in candidates for item in candidate.marking_refs})
    marking_objects: list[dict[str, object]] = []
    if marking_ids:
        outcomes = list(
            (
                await session.scalars(
                    select(ImportObjectOutcome).where(
                        ImportObjectOutcome.external_id.in_(marking_ids)
                    )
                )
            ).all()
        )
        definitions = {
            item.external_id: item.raw_record
            for item in outcomes
            if item.raw_record.get("type") == "marking-definition"
        }
        marking_objects = [definitions[item] for item in marking_ids if item in definitions]
    objects = [*marking_objects, *(candidate.stix_object for candidate in candidates)]
    bundle: dict[str, object] = {
        "type": "bundle",
        "id": f"bundle--{uuid4()}",
        "objects": objects,
    }
    return bundle, candidates


def bundle_hash(bundle: dict[str, object]) -> str:
    encoded = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_frozen_bundle(
    bundle: dict[str, object], expected_hash: str, policy: TaxiiExportPolicy
) -> list[dict[str, object]]:
    if bundle_hash(bundle) != expected_hash:
        raise ExportValidationError("Frozen STIX bundle hash does not match its approval record")
    raw_objects = bundle.get("objects")
    if not isinstance(raw_objects, list) or not all(isinstance(item, dict) for item in raw_objects):
        raise ExportValidationError("Frozen STIX bundle contains an invalid objects list")
    objects: list[dict[str, object]] = list(raw_objects)
    indicators = [item for item in objects if item.get("type") == "indicator"]
    if not indicators or len(indicators) > policy.max_objects:
        raise ExportValidationError("Frozen STIX bundle violates the current object budget")
    allowed = set(policy.allowed_marking_refs)
    for indicator in indicators:
        markings = _marking_refs(indicator)
        if not markings and not policy.allow_unmarked:
            raise ExportValidationError("Current policy no longer allows an unmarked STIX object")
        if set(markings) - allowed:
            raise ExportValidationError("Current policy no longer allows every STIX object marking")
    return objects

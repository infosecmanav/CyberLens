import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.collection import get_or_create_entity
from app.intelligence.normalization import NormalizationError, NormalizedEntity, normalize_entity
from app.models import Entity, Observation, Source, SourceRecord
from app.models.enums import EntityType, SourceHealth
from app.operations.audit import emit_audit

STIX_IMPORT_SOURCE_ID = "manual-stix-2-1"
MAX_STIX_BUNDLE_BYTES = 2 * 1024 * 1024

_PATTERN_MAPPINGS: tuple[tuple[re.Pattern[str], EntityType], ...] = (
    (re.compile(r"^\[\s*ipv4-addr:value\s*=\s*'((?:\\.|[^'])+)'\s*\]$"), EntityType.IPV4),
    (re.compile(r"^\[\s*ipv6-addr:value\s*=\s*'((?:\\.|[^'])+)'\s*\]$"), EntityType.IPV6),
    (re.compile(r"^\[\s*domain-name:value\s*=\s*'((?:\\.|[^'])+)'\s*\]$"), EntityType.DOMAIN),
    (re.compile(r"^\[\s*url:value\s*=\s*'((?:\\.|[^'])+)'\s*\]$"), EntityType.URL),
    (re.compile(r"^\[\s*email-addr:value\s*=\s*'((?:\\.|[^'])+)'\s*\]$"), EntityType.EMAIL),
    (re.compile(r"^\[\s*file:hashes\.'MD5'\s*=\s*'((?:\\.|[^'])+)'\s*\]$"), EntityType.MD5),
    (re.compile(r"^\[\s*file:hashes\.'SHA-1'\s*=\s*'((?:\\.|[^'])+)'\s*\]$"), EntityType.SHA1),
    (re.compile(r"^\[\s*file:hashes\.'SHA-256'\s*=\s*'((?:\\.|[^'])+)'\s*\]$"), EntityType.SHA256),
)
_STIX_ID = re.compile(r"^indicator--[0-9a-fA-F-]{36}$")


@dataclass(frozen=True)
class StixIssue:
    object_index: int
    external_id: str | None
    disposition: Literal["REJECTED", "SKIPPED"]
    code: str
    message: str


@dataclass(frozen=True)
class ParsedStixIndicator:
    external_id: str
    normalized: NormalizedEntity
    observed_at: datetime
    published_at: datetime
    valid_until: datetime | None
    confidence: float | None
    source_reference: str | None
    attributes: dict[str, Any]
    raw_record: dict[str, Any]


@dataclass(frozen=True)
class PersistedStixIndicator:
    entity_id: UUID
    observation_id: UUID
    entity_type: EntityType
    normalized_value: str
    external_id: str
    deduplicated: bool


@dataclass(frozen=True)
class StixImportSummary:
    bundle_id: str
    received_objects: int
    items: list[PersistedStixIndicator]
    issues: list[StixIssue]
    created_entities: int
    reused_entities: int

    @property
    def imported_observations(self) -> int:
        return sum(not item.deduplicated for item in self.items)

    @property
    def deduplicated_observations(self) -> int:
        return sum(item.deduplicated for item in self.items)

    @property
    def rejected_objects(self) -> int:
        return sum(issue.disposition == "REJECTED" for issue in self.issues)

    @property
    def skipped_objects(self) -> int:
        return sum(issue.disposition == "SKIPPED" for issue in self.issues)


def canonical_bundle_size(bundle: dict[str, Any]) -> int:
    return len(json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode())


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _optional_timestamp(value: object, field: str) -> datetime | None:
    return None if value is None else _timestamp(value, field)


def _pattern_entity(pattern: object) -> NormalizedEntity:
    if not isinstance(pattern, str) or len(pattern) > 4096:
        raise ValueError("pattern must be a STIX pattern no longer than 4096 characters")
    for expression, entity_type in _PATTERN_MAPPINGS:
        match = expression.fullmatch(pattern)
        if match is None:
            continue
        value = match.group(1).replace(r"\'", "'").replace(r"\\", "\\")
        try:
            return normalize_entity(value, entity_type)
        except NormalizationError as exc:
            raise ValueError(str(exc)) from exc
    raise ValueError("pattern must contain one supported equality comparison")


def _safe_external_reference(value: object) -> str | None:
    if not isinstance(value, list):
        return None
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            continue
        url = item["url"]
        parsed = urlsplit(url)
        if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username:
            return url[:1000]
    return None


def _string_list(value: object, maximum: int = 100) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item[:500] for item in value[:maximum] if isinstance(item, str)]


def _parse_indicator(item: dict[str, Any]) -> ParsedStixIndicator:
    external_id = item.get("id")
    if not isinstance(external_id, str) or _STIX_ID.fullmatch(external_id) is None:
        raise ValueError("indicator id must use the indicator--UUID form")
    if item.get("spec_version") != "2.1":
        raise ValueError("only STIX 2.1 Indicator objects are accepted")
    if item.get("pattern_type") != "stix":
        raise ValueError("pattern_type must be stix")
    pattern_version = item.get("pattern_version")
    if pattern_version not in (None, "2.1"):
        raise ValueError("pattern_version must be 2.1 when provided")
    normalized = _pattern_entity(item.get("pattern"))
    observed_at = _timestamp(item.get("valid_from"), "valid_from")
    valid_until = _optional_timestamp(item.get("valid_until"), "valid_until")
    if valid_until is not None and valid_until < observed_at:
        raise ValueError("valid_until cannot be earlier than valid_from")
    published_at = _optional_timestamp(item.get("modified"), "modified")
    if published_at is None:
        published_at = _optional_timestamp(item.get("created"), "created") or observed_at
    confidence_value = item.get("confidence")
    confidence: float | None = None
    if confidence_value is not None:
        if isinstance(confidence_value, bool) or not isinstance(confidence_value, int):
            raise ValueError("confidence must be an integer from 0 through 100")
        if not 0 <= confidence_value <= 100:
            raise ValueError("confidence must be an integer from 0 through 100")
        confidence = confidence_value / 100
    attributes: dict[str, Any] = {
        "stix_id": external_id,
        "spec_version": "2.1",
        "pattern": item["pattern"],
        "pattern_type": "stix",
        "pattern_version": pattern_version or "2.1",
        "created_by_ref": item.get("created_by_ref"),
        "object_marking_refs": _string_list(item.get("object_marking_refs")),
        "labels": _string_list(item.get("labels")),
        "confidence": confidence_value,
    }
    return ParsedStixIndicator(
        external_id=external_id,
        normalized=normalized,
        observed_at=observed_at,
        published_at=published_at,
        valid_until=valid_until,
        confidence=confidence,
        source_reference=_safe_external_reference(item.get("external_references")),
        attributes=attributes,
        raw_record=item,
    )


def parse_stix_objects(
    objects: list[dict[str, Any]],
) -> tuple[list[ParsedStixIndicator], list[StixIssue]]:
    parsed: list[ParsedStixIndicator] = []
    issues: list[StixIssue] = []
    for index, item in enumerate(objects):
        external_id = item.get("id") if isinstance(item.get("id"), str) else None
        if item.get("type") != "indicator":
            issues.append(
                StixIssue(
                    object_index=index,
                    external_id=external_id,
                    disposition="SKIPPED",
                    code="UNSUPPORTED_OBJECT_TYPE",
                    message="Only STIX Indicator objects are imported in this iteration.",
                )
            )
            continue
        try:
            parsed.append(_parse_indicator(item))
        except ValueError as exc:
            issues.append(
                StixIssue(
                    object_index=index,
                    external_id=external_id,
                    disposition="REJECTED",
                    code="INVALID_INDICATOR",
                    message=str(exc),
                )
            )
    return parsed, issues


def _content_hash(record: dict[str, Any]) -> str:
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


async def import_stix_bundle(
    session: AsyncSession,
    *,
    bundle_id: str,
    objects: list[dict[str, Any]],
    source_reference: str | None,
    actor_id: UUID,
) -> StixImportSummary:
    source = await session.scalar(select(Source).where(Source.source_id == STIX_IMPORT_SOURCE_ID))
    if source is None:
        raise RuntimeError("The manual STIX import source is not seeded")
    parsed, issues = parse_stix_objects(objects)
    items: list[PersistedStixIndicator] = []
    created_entity_ids: set[UUID] = set()
    reused_entity_ids: set[UUID] = set()
    retrieved_at = datetime.now(UTC)
    provenance = source_reference or f"stix:{bundle_id}"

    for indicator in parsed:
        existing_entity = await session.scalar(
            select(Entity).where(
                Entity.entity_type == indicator.normalized.entity_type,
                Entity.normalized_value == indicator.normalized.normalized_value,
            )
        )
        entity = await get_or_create_entity(session, indicator.normalized)
        if existing_entity is None:
            created_entity_ids.add(entity.id)
        elif entity.id not in created_entity_ids:
            reused_entity_ids.add(entity.id)

        content_hash = _content_hash(indicator.raw_record)
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
                external_id=indicator.external_id,
                source_reference=indicator.source_reference or source_reference,
                published_at=indicator.published_at,
                retrieved_at=retrieved_at,
                content_hash=content_hash,
                raw_record=indicator.raw_record,
            )
            session.add(source_record)
            await session.flush()
        observation = await session.scalar(
            select(Observation).where(
                Observation.source_record_id == source_record.id,
                Observation.observation_type == "STIX_INDICATOR",
            )
        )
        deduplicated = observation is not None
        if observation is None:
            observation = Observation(
                entity_id=entity.id,
                source_id=source.id,
                source_record_id=source_record.id,
                observation_type="STIX_INDICATOR",
                summary=(
                    f"Imported STIX 2.1 indicator for {indicator.normalized.entity_type.value} "
                    f"{indicator.normalized.normalized_value}."
                ),
                observed_at=indicator.observed_at,
                valid_until=indicator.valid_until,
                confidence=indicator.confidence,
                source_reference=indicator.source_reference or source_reference,
                upstream_provenance=provenance[:500],
                raw_record=indicator.attributes,
            )
            session.add(observation)
            await session.flush()
        items.append(
            PersistedStixIndicator(
                entity_id=entity.id,
                observation_id=observation.id,
                entity_type=indicator.normalized.entity_type,
                normalized_value=indicator.normalized.normalized_value,
                external_id=indicator.external_id,
                deduplicated=deduplicated,
            )
        )

    source.last_checked = retrieved_at
    if items:
        source.health_status = SourceHealth.HEALTHY
        source.last_success = retrieved_at
        source.last_error = None
    summary = StixImportSummary(
        bundle_id=bundle_id,
        received_objects=len(objects),
        items=items,
        issues=issues,
        created_entities=len(created_entity_ids),
        reused_entities=len(reused_entity_ids),
    )
    emit_audit(
        session,
        actor_id=actor_id,
        action="intelligence.stix_bundle_imported",
        object_type="stix_bundle",
        object_id=bundle_id,
        details={
            "source_id": STIX_IMPORT_SOURCE_ID,
            "received_objects": summary.received_objects,
            "accepted_objects": len(summary.items),
            "imported_observations": summary.imported_observations,
            "deduplicated_observations": summary.deduplicated_observations,
            "rejected_objects": summary.rejected_objects,
            "skipped_objects": summary.skipped_objects,
        },
    )
    await session.commit()
    return summary

from collections.abc import Sequence
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

from app.models.enums import EvidenceDimension, EvidencePolarity

_OBSERVATION_DIMENSIONS: dict[str, EvidenceDimension] = {
    "ATTACK_TECHNIQUE": EvidenceDimension.BEHAVIORAL_ASSOCIATION,
    "BENIGN_CLASSIFICATION": EvidenceDimension.MALICIOUSNESS,
    "BOTNET_COMMAND_AND_CONTROL": EvidenceDimension.MALICIOUSNESS,
    "CERTIFICATE_TRANSPARENCY": EvidenceDimension.INFRASTRUCTURE_ASSOCIATION,
    "COMMUNITY_ABUSE_REPORTS": EvidenceDimension.MALICIOUSNESS,
    "CVE_RECORD": EvidenceDimension.VULNERABILITY_CONTEXT,
    "INTERNET_EXPOSURE": EvidenceDimension.INFRASTRUCTURE_ASSOCIATION,
    "INTERNET_SCANNER_CONTEXT": EvidenceDimension.INFRASTRUCTURE_ASSOCIATION,
    "KNOWN_EXPLOITED_VULNERABILITY": EvidenceDimension.MALICIOUSNESS,
    "MALWARE_DISTRIBUTION_CONTEXT": EvidenceDimension.MALWARE_ASSOCIATION,
    "MALWARE_SAMPLE_CONTEXT": EvidenceDimension.MALWARE_ASSOCIATION,
    "NVD_CVE": EvidenceDimension.VULNERABILITY_CONTEXT,
    "PHISHING_URL_FEED_ENTRY": EvidenceDimension.MALICIOUSNESS,
    "REGISTRATION_CONTEXT": EvidenceDimension.INFRASTRUCTURE_ASSOCIATION,
    "THREATFOX_IOC_MATCH": EvidenceDimension.MALWARE_ASSOCIATION,
    "URLSCAN_SEARCH_CONTEXT": EvidenceDimension.INFRASTRUCTURE_ASSOCIATION,
    "VIRUSTOTAL_REPUTATION": EvidenceDimension.MALICIOUSNESS,
    "VULNERABILITY_ADVISORY": EvidenceDimension.VULNERABILITY_CONTEXT,
}


def classify_evidence_dimension(observation_type: str) -> EvidenceDimension:
    """Map known normalized observation types without inferring beyond their contract."""
    return _OBSERVATION_DIMENSIONS.get(
        observation_type.upper(), EvidenceDimension.GENERAL_CONTEXT
    )


@dataclass(frozen=True)
class EvidenceSignal:
    evidence_id: str
    observation_id: str
    source_id: str
    polarity: EvidencePolarity
    assessment_dimension: EvidenceDimension
    source_reference: str | None
    upstream_provenance: str | None
    source_record_id: str | None


@dataclass
class _ProvenanceGroup:
    reference: str | None
    sources: set[str] = field(default_factory=set)
    polarities: set[str] = field(default_factory=set)
    dimensions: set[str] = field(default_factory=set)
    evidence_ids: set[str] = field(default_factory=set)


def _canonical_reference(value: str) -> str:
    cleaned = value.strip()
    parsed = urlsplit(cleaned)
    if parsed.scheme and parsed.netloc:
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit(
            (parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, "")
        )
    return cleaned.rstrip("/")


def _group_identity(signal: EvidenceSignal) -> tuple[str, str | None]:
    reference = signal.source_reference or signal.upstream_provenance
    if reference:
        canonical = _canonical_reference(reference)
        return f"reference:{canonical}", canonical
    local_id = signal.source_record_id or signal.observation_id
    return f"provider-record:{signal.source_id}:{local_id}", None


def _build_groups(signals: Sequence[EvidenceSignal]) -> dict[str, _ProvenanceGroup]:
    groups: dict[str, _ProvenanceGroup] = {}
    for signal in signals:
        identity, reference = _group_identity(signal)
        group = groups.setdefault(identity, _ProvenanceGroup(reference=reference))
        group.sources.add(signal.source_id)
        group.polarities.add(signal.polarity.value)
        group.dimensions.add(signal.assessment_dimension.value)
        group.evidence_ids.add(signal.evidence_id)
    return groups


def _shared_groups(groups: dict[str, _ProvenanceGroup]) -> list[dict[str, object]]:
    shared = [
        {
            "reference": group.reference,
            "sources": sorted(group.sources),
            "polarities": sorted(group.polarities),
            "dimensions": sorted(group.dimensions),
            "evidence_count": len(group.evidence_ids),
        }
        for group in groups.values()
        if group.reference is not None and len(group.sources) > 1
    ]
    shared.sort(key=lambda item: str(item["reference"]))
    return shared


def _group_polarity_count(
    groups: dict[str, _ProvenanceGroup], polarity: EvidencePolarity
) -> int:
    return sum(polarity.value in group.polarities for group in groups.values())


def _dimension_status(
    signals: Sequence[EvidenceSignal],
    groups: dict[str, _ProvenanceGroup],
    shared_groups: list[dict[str, object]],
) -> str:
    supporting_groups = _group_polarity_count(groups, EvidencePolarity.SUPPORTS)
    conflicting_groups = _group_polarity_count(groups, EvidencePolarity.CONFLICTS)
    providers = {signal.source_id for signal in signals}
    if supporting_groups and conflicting_groups:
        return "CONFLICTING_EVIDENCE"
    if supporting_groups >= 2:
        return "INDEPENDENT_CORROBORATION"
    if shared_groups:
        return "SHARED_UPSTREAM_REPORTING"
    if len(providers) == 1:
        return "SINGLE_SOURCE"
    return "MULTI_SOURCE_CONTEXT"


def _count(summary: dict[str, object], key: str) -> int:
    value = summary.get(key)
    return value if isinstance(value, int) else 0


def _summarize_dimension(
    dimension: EvidenceDimension, signals: Sequence[EvidenceSignal]
) -> dict[str, object]:
    groups = _build_groups(signals)
    shared_groups = _shared_groups(groups)
    polarity_counts = {
        polarity: sum(signal.polarity == polarity for signal in signals)
        for polarity in EvidencePolarity
    }
    return {
        "dimension": dimension.value,
        "status": _dimension_status(signals, groups, shared_groups),
        "evidence_count": len(signals),
        "provider_count": len({signal.source_id for signal in signals}),
        "provenance_group_count": len(groups),
        "supporting_evidence": polarity_counts[EvidencePolarity.SUPPORTS],
        "conflicting_evidence": polarity_counts[EvidencePolarity.CONFLICTS],
        "contextual_evidence": polarity_counts[EvidencePolarity.CONTEXTUAL],
        "supporting_provenance_groups": _group_polarity_count(
            groups, EvidencePolarity.SUPPORTS
        ),
        "conflicting_provenance_groups": _group_polarity_count(
            groups, EvidencePolarity.CONFLICTS
        ),
    }


def reconcile_evidence(signals: Sequence[EvidenceSignal]) -> dict[str, object]:
    groups = _build_groups(signals)
    shared_groups = _shared_groups(groups)
    polarity_counts = {
        polarity: sum(signal.polarity == polarity for signal in signals)
        for polarity in EvidencePolarity
    }
    providers = {signal.source_id for signal in signals}
    by_dimension: dict[EvidenceDimension, list[EvidenceSignal]] = {}
    for signal in signals:
        by_dimension.setdefault(signal.assessment_dimension, []).append(signal)
    dimension_summaries = [
        _summarize_dimension(dimension, by_dimension[dimension])
        for dimension in sorted(by_dimension, key=lambda item: item.value)
    ]
    dimension_statuses = {str(item["status"]) for item in dimension_summaries}
    supporting_groups = max(
        (_count(item, "supporting_provenance_groups") for item in dimension_summaries),
        default=0,
    )
    conflicting_groups = max(
        (_count(item, "conflicting_provenance_groups") for item in dimension_summaries),
        default=0,
    )

    if not signals:
        status = "NO_EVIDENCE"
        independence = "NONE"
        summary = "No source-backed evidence is available for cross-validation."
    elif "CONFLICTING_EVIDENCE" in dimension_statuses:
        status = "CONFLICTING_EVIDENCE"
        independence = "CONTESTED"
        summary = "At least one analytical dimension contains supporting and conflicting evidence."
    elif "INDEPENDENT_CORROBORATION" in dimension_statuses:
        status = "INDEPENDENT_CORROBORATION"
        independence = "MULTIPLE_PROVENANCE_GROUPS"
        summary = "Supporting evidence aligns within a dimension across provenance groups."
    elif shared_groups:
        status = "SHARED_UPSTREAM_REPORTING"
        independence = "LIMITED"
        summary = "Multiple providers repeat at least one shared upstream reference."
    elif len(providers) == 1:
        status = "SINGLE_SOURCE"
        independence = "MINIMAL"
        summary = "Evidence is currently limited to one direct provider."
    else:
        status = "MULTI_SOURCE_CONTEXT"
        independence = "LIMITED"
        summary = (
            "Evidence spans providers, but no analytical dimension has independently "
            "corroborated support."
        )

    limitations: list[str] = []
    if not signals:
        limitations.append("No evidence was available to reconcile.")
    if len(dimension_summaries) > 1:
        limitations.append(
            "Evidence in different analytical dimensions is not counted as corroboration."
        )
    if shared_groups:
        limitations.append(
            "Provider count exceeds independent provenance for shared upstream reporting."
        )
    if status == "CONFLICTING_EVIDENCE":
        limitations.append(
            "Same-dimension conflicting evidence requires an analyst decision."
        )
    elif polarity_counts[EvidencePolarity.CONFLICTS]:
        limitations.append(
            "Conflicting evidence in another dimension does not automatically negate a claim."
        )
    if polarity_counts[EvidencePolarity.CONTEXTUAL] and not supporting_groups:
        limitations.append("Contextual observations do not establish maliciousness.")
    if EvidenceDimension.GENERAL_CONTEXT in by_dimension:
        limitations.append(
            "General-context evidence is broad and requires analyst classification for "
            "precise alignment."
        )
    limitations.append(
        "Independence is based on normalized provenance references and is not a probability."
    )

    return {
        "status": status,
        "independence": independence,
        "summary": summary,
        "evidence_count": len(signals),
        "provider_count": len(providers),
        "provenance_group_count": len(groups),
        "dimension_count": len(dimension_summaries),
        "supporting_evidence": polarity_counts[EvidencePolarity.SUPPORTS],
        "conflicting_evidence": polarity_counts[EvidencePolarity.CONFLICTS],
        "contextual_evidence": polarity_counts[EvidencePolarity.CONTEXTUAL],
        "supporting_provenance_groups": supporting_groups,
        "conflicting_provenance_groups": conflicting_groups,
        "dimension_summaries": dimension_summaries,
        "shared_upstream_groups": shared_groups,
        "limitations": limitations,
    }

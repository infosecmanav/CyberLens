from collections.abc import Sequence
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

from app.models.enums import EvidencePolarity


@dataclass(frozen=True)
class EvidenceSignal:
    evidence_id: str
    observation_id: str
    source_id: str
    polarity: EvidencePolarity
    source_reference: str | None
    upstream_provenance: str | None
    source_record_id: str | None


@dataclass
class _ProvenanceGroup:
    reference: str | None
    sources: set[str] = field(default_factory=set)
    polarities: set[str] = field(default_factory=set)
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


def reconcile_evidence(signals: Sequence[EvidenceSignal]) -> dict[str, object]:
    groups: dict[str, _ProvenanceGroup] = {}
    polarity_counts = {polarity.value: 0 for polarity in EvidencePolarity}
    providers = {signal.source_id for signal in signals}

    for signal in signals:
        polarity_counts[signal.polarity.value] += 1
        identity, reference = _group_identity(signal)
        group = groups.setdefault(identity, _ProvenanceGroup(reference=reference))
        group.sources.add(signal.source_id)
        group.polarities.add(signal.polarity.value)
        group.evidence_ids.add(signal.evidence_id)

    supporting_groups = sum(
        EvidencePolarity.SUPPORTS.value in group.polarities for group in groups.values()
    )
    conflicting_groups = sum(
        EvidencePolarity.CONFLICTS.value in group.polarities for group in groups.values()
    )
    shared_groups = [
        {
            "reference": group.reference,
            "sources": sorted(group.sources),
            "polarities": sorted(group.polarities),
            "evidence_count": len(group.evidence_ids),
        }
        for group in groups.values()
        if group.reference is not None and len(group.sources) > 1
    ]
    shared_groups.sort(key=lambda item: str(item["reference"]))

    if not signals:
        status = "NO_EVIDENCE"
        independence = "NONE"
        summary = "No source-backed evidence is available for cross-validation."
    elif supporting_groups and conflicting_groups:
        status = "CONFLICTING_EVIDENCE"
        independence = "CONTESTED"
        summary = "Supporting and conflicting evidence are both present and require review."
    elif supporting_groups >= 2:
        status = "INDEPENDENT_CORROBORATION"
        independence = "MULTIPLE_PROVENANCE_GROUPS"
        summary = "Supporting evidence is present in multiple provenance groups."
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
        summary = "Multiple providers add context without independent supporting evidence."

    limitations: list[str] = []
    if not signals:
        limitations.append("No evidence was available to reconcile.")
    if shared_groups:
        limitations.append(
            "Provider count exceeds independent provenance for shared upstream reporting."
        )
    if conflicting_groups:
        limitations.append("Conflicting evidence requires an analyst decision.")
    if polarity_counts[EvidencePolarity.CONTEXTUAL.value] and not supporting_groups:
        limitations.append("Contextual observations do not establish maliciousness.")
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
        "supporting_evidence": polarity_counts[EvidencePolarity.SUPPORTS.value],
        "conflicting_evidence": polarity_counts[EvidencePolarity.CONFLICTS.value],
        "contextual_evidence": polarity_counts[EvidencePolarity.CONTEXTUAL.value],
        "supporting_provenance_groups": supporting_groups,
        "conflicting_provenance_groups": conflicting_groups,
        "shared_upstream_groups": shared_groups,
        "limitations": limitations,
    }

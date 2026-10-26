from app.investigations.cross_validation import EvidenceSignal, reconcile_evidence
from app.models.enums import EvidencePolarity


def signal(
    evidence_id: str,
    source_id: str,
    polarity: EvidencePolarity,
    reference: str | None,
) -> EvidenceSignal:
    return EvidenceSignal(
        evidence_id=evidence_id,
        observation_id=f"observation-{evidence_id}",
        source_id=source_id,
        polarity=polarity,
        source_reference=reference,
        upstream_provenance=None,
        source_record_id=f"record-{evidence_id}",
    )


def test_reconciliation_reports_no_evidence_without_inventing_confidence() -> None:
    result = reconcile_evidence([])

    assert result["status"] == "NO_EVIDENCE"
    assert result["independence"] == "NONE"
    assert result["evidence_count"] == 0
    assert "probability" not in result


def test_reconciliation_normalizes_references_and_preserves_conflict() -> None:
    result = reconcile_evidence(
        [
            signal(
                "support",
                "provider-a",
                EvidencePolarity.SUPPORTS,
                "HTTPS://UPSTREAM.EXAMPLE/reports/42/",
            ),
            signal(
                "conflict",
                "provider-b",
                EvidencePolarity.CONFLICTS,
                "https://upstream.example/reports/42",
            ),
        ]
    )

    assert result["status"] == "CONFLICTING_EVIDENCE"
    assert result["provider_count"] == 2
    assert result["provenance_group_count"] == 1
    assert result["supporting_provenance_groups"] == 1
    assert result["conflicting_provenance_groups"] == 1
    assert result["shared_upstream_groups"] == [
        {
            "reference": "https://upstream.example/reports/42",
            "sources": ["provider-a", "provider-b"],
            "polarities": ["CONFLICTS", "SUPPORTS"],
            "evidence_count": 2,
        }
    ]

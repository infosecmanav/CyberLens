from app.investigations.cross_validation import (
    EvidenceSignal,
    classify_evidence_dimension,
    reconcile_evidence,
)
from app.models.enums import EvidenceDimension, EvidencePolarity


def signal(
    evidence_id: str,
    source_id: str,
    polarity: EvidencePolarity,
    reference: str | None,
    dimension: EvidenceDimension = EvidenceDimension.MALICIOUSNESS,
) -> EvidenceSignal:
    return EvidenceSignal(
        evidence_id=evidence_id,
        observation_id=f"observation-{evidence_id}",
        source_id=source_id,
        polarity=polarity,
        assessment_dimension=dimension,
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


def test_observation_dimension_mapping_is_conservative() -> None:
    assert (
        classify_evidence_dimension("KNOWN_EXPLOITED_VULNERABILITY")
        == EvidenceDimension.MALICIOUSNESS
    )
    assert (
        classify_evidence_dimension("MALWARE_SAMPLE_CONTEXT")
        == EvidenceDimension.MALWARE_ASSOCIATION
    )
    assert (
        classify_evidence_dimension("UNRECOGNIZED_PROVIDER_CLAIM")
        == EvidenceDimension.GENERAL_CONTEXT
    )


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
            "dimensions": ["MALICIOUSNESS"],
            "evidence_count": 2,
        }
    ]


def test_cross_dimension_support_is_context_not_corroboration() -> None:
    result = reconcile_evidence(
        [
            signal(
                "malware",
                "provider-a",
                EvidencePolarity.SUPPORTS,
                "https://provider-a.example/report",
                EvidenceDimension.MALWARE_ASSOCIATION,
            ),
            signal(
                "infrastructure",
                "provider-b",
                EvidencePolarity.SUPPORTS,
                "https://provider-b.example/report",
                EvidenceDimension.INFRASTRUCTURE_ASSOCIATION,
            ),
        ]
    )

    assert result["status"] == "MULTI_SOURCE_CONTEXT"
    assert result["dimension_count"] == 2
    assert result["supporting_provenance_groups"] == 1
    assert {
        (item["dimension"], item["status"])
        for item in result["dimension_summaries"]
    } == {
        ("INFRASTRUCTURE_ASSOCIATION", "SINGLE_SOURCE"),
        ("MALWARE_ASSOCIATION", "SINGLE_SOURCE"),
    }
    assert (
        "Evidence in different analytical dimensions is not counted as corroboration."
        in result["limitations"]
    )


def test_cross_dimension_conflict_does_not_negate_an_unrelated_claim() -> None:
    result = reconcile_evidence(
        [
            signal(
                "support",
                "provider-a",
                EvidencePolarity.SUPPORTS,
                "https://provider-a.example/report",
                EvidenceDimension.MALWARE_ASSOCIATION,
            ),
            signal(
                "conflict",
                "provider-b",
                EvidencePolarity.CONFLICTS,
                "https://provider-b.example/report",
                EvidenceDimension.INFRASTRUCTURE_ASSOCIATION,
            ),
        ]
    )

    assert result["status"] == "MULTI_SOURCE_CONTEXT"
    assert "CONFLICTING_EVIDENCE" not in {
        item["status"] for item in result["dimension_summaries"]
    }
    assert (
        "Conflicting evidence in another dimension does not automatically negate a claim."
        in result["limitations"]
    )

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.intelligence.stix_import import parse_stix_objects

FIXTURES = Path(__file__).parent / "fixtures" / "stix"


def load_bundle(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("pattern", "entity_type", "normalized_value"),
    [
        ("[ipv4-addr:value = '198.51.100.42']", "IPV4", "198.51.100.42"),
        ("[ipv6-addr:value = '2001:0db8::1']", "IPV6", "2001:db8::1"),
        ("[domain-name:value = 'Example.TEST.']", "DOMAIN", "example.test"),
        ("[url:value = 'HTTPS://Example.TEST:443/path#fragment']", "URL", "https://example.test/path"),
        ("[email-addr:value = 'Analyst@Example.TEST']", "EMAIL", "analyst@example.test"),
        ("[file:hashes.'MD5' = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA']", "MD5", "a" * 32),
        ("[file:hashes.'SHA-1' = 'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB']", "SHA1", "b" * 40),
        ("[file:hashes.'SHA-256' = '" + "C" * 64 + "']", "SHA256", "c" * 64),
    ],
)
def test_stix_parser_maps_every_declared_ioc_type(
    pattern: str, entity_type: str, normalized_value: str
) -> None:
    objects = [
        {
            "type": "indicator",
            "spec_version": "2.1",
            "id": "indicator--99999999-9999-4999-8999-999999999999",
            "valid_from": "2026-10-22T12:00:00Z",
            "pattern_type": "stix",
            "pattern": pattern,
        }
    ]
    parsed, issues = parse_stix_objects(objects)
    assert issues == []
    assert parsed[0].normalized.entity_type == entity_type
    assert parsed[0].normalized.normalized_value == normalized_value


def test_stix_import_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={"bundle": load_bundle("valid_bundle.json")},
    )
    assert response.status_code == 401
    assert client.get("/api/v1/intelligence/imports").status_code == 401
    assert client.post(
        "/api/v1/intelligence/imports/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/objects/"
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/promote",
        json={
            "polarity": "CONTEXTUAL",
            "claim": "Reviewed indicator context.",
            "uncertainty_notes": "Provider scope remains a limitation.",
        },
    ).status_code == 401


def test_stix_import_preserves_provenance_and_reports_unsupported_objects(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={
            "bundle": load_bundle("valid_bundle.json"),
            "source_reference": "https://example.test/exchange/collection-1",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["import_id"]
    assert payload["source_id"] == "manual-stix-2-1"
    assert payload["received_objects"] == 3
    assert payload["accepted_objects"] == 2
    assert payload["imported_observations"] == 2
    assert payload["created_entities"] == 2
    assert payload["skipped_objects"] == 1
    assert payload["rejected_objects"] == 0
    assert payload["filtered_objects"] == 0
    assert payload["filter_definition"] == {}
    assert {item["normalized_value"] for item in payload["items"]} == {
        "example.test",
        "a" * 64,
    }
    assert payload["issues"][0]["code"] == "UNSUPPORTED_OBJECT_TYPE"

    domain = next(item for item in payload["items"] if item["entity_type"] == "DOMAIN")
    observations = client.get(
        f"/api/v1/intelligence/entities/{domain['entity_id']}/observations"
    )
    assert observations.status_code == 200
    observation = observations.json()[0]
    assert observation["source_id"] == "manual-stix-2-1"
    assert observation["confidence"] == 0.85
    assert observation["source_reference"] == "https://example.test/advisories/2222"
    assert observation["attributes"]["object_marking_refs"] == [
        "marking-definition--bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    ]

    audit = client.get("/api/v1/audit", headers=auth_headers)
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "intelligence.stix_bundle_imported"
    assert audit.json()[0]["details"]["imported_observations"] == 2


def test_stix_reimport_is_idempotent(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    request = {"bundle": load_bundle("valid_bundle.json")}
    first = client.post(
        "/api/v1/intelligence/imports/stix-bundles", json=request, headers=auth_headers
    )
    second = client.post(
        "/api/v1/intelligence/imports/stix-bundles", json=request, headers=auth_headers
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["imported_observations"] == 0
    assert second.json()["deduplicated_observations"] == 2
    assert first.json()["import_id"] != second.json()["import_id"]
    assert [item["observation_id"] for item in first.json()["items"]] == [
        item["observation_id"] for item in second.json()["items"]
    ]


def test_stix_import_accepts_valid_records_and_reports_rejected_records(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={"bundle": load_bundle("partial_bundle.json")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_objects"] == 1
    assert payload["imported_observations"] == 1
    assert payload["rejected_objects"] == 2
    assert payload["skipped_objects"] == 0
    assert payload["items"][0]["normalized_value"] == "198.51.100.42"
    assert {issue["message"] for issue in payload["issues"]} == {
        "pattern must contain one supported equality comparison",
        "only STIX 2.1 Indicator objects are accepted",
    }


def test_stix_import_rejects_invalid_bundle_contract(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={"bundle": {"type": "collection", "id": "not-a-bundle", "objects": []}},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_stix_import_enforces_object_count_limit(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={
            "bundle": {
                "type": "bundle",
                "id": "bundle--aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "objects": [{}] * 501,
            }
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_stix_import_enforces_serialized_size_limit(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    bundle = load_bundle("partial_bundle.json")
    bundle["objects"] = [bundle["objects"][0]]
    bundle["objects"][0]["description"] = "x" * (2 * 1024 * 1024)
    response = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={"bundle": bundle},
        headers=auth_headers,
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "STIX bundle exceeds the 2 MiB import limit"


@pytest.mark.parametrize(
    ("filters", "expected_code"),
    [
        ({"entity_types": ["DOMAIN"]}, "FILTER_ENTITY_TYPE"),
        ({"minimum_confidence": 80}, "FILTER_MINIMUM_CONFIDENCE"),
        ({"valid_from_end": "2026-10-20T23:59:59Z"}, "FILTER_VALID_FROM_WINDOW"),
        (
            {
                "required_marking_refs": [
                    "marking-definition--bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
                ]
            },
            "FILTER_REQUIRED_MARKING",
        ),
    ],
)
def test_stix_import_applies_and_persists_reproducible_filters(
    client: TestClient,
    auth_headers: dict[str, str],
    filters: dict[str, Any],
    expected_code: str,
) -> None:
    bundle = load_bundle("valid_bundle.json")
    bundle["objects"] = bundle["objects"][:2]
    response = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={"bundle": bundle, "filters": filters},
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["received_objects"] == 2
    assert payload["accepted_objects"] == 1
    assert payload["filtered_objects"] == 1
    assert payload["skipped_objects"] == 0
    expected_definition = filters.copy()
    if "valid_from_end" in expected_definition:
        expected_definition["valid_from_end"] = "2026-10-20T23:59:59+00:00"
    assert payload["filter_definition"] == expected_definition
    assert payload["items"][0]["normalized_value"] == "example.test"
    filtered_issue = next(
        issue for issue in payload["issues"] if issue["disposition"] == "FILTERED"
    )
    assert filtered_issue["code"] == expected_code

    detail = client.get(
        f"/api/v1/intelligence/imports/{payload['import_id']}", headers=auth_headers
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "COMPLETED"
    assert detail.json()["filter_definition"] == expected_definition
    assert detail.json()["filtered_objects"] == 1
    filtered_outcome = next(
        item for item in detail.json()["objects"] if item["disposition"] == "FILTERED"
    )
    assert filtered_outcome["code"] == expected_code
    assert filtered_outcome["raw_record"]["type"] == "indicator"
    assert filtered_outcome["entity_id"] is None
    assert filtered_outcome["observation_id"] is None

    clean_history = client.get(
        "/api/v1/intelligence/imports?has_issues=false", headers=auth_headers
    )
    assert clean_history.status_code == 200
    assert clean_history.json()["total"] == 1


@pytest.mark.parametrize(
    "filters",
    [
        {"entity_types": ["CVE"]},
        {
            "valid_from_start": "2026-10-22T00:00:00Z",
            "valid_from_end": "2026-10-21T00:00:00Z",
        },
        {"required_marking_refs": ["not-a-marking-definition"]},
    ],
)
def test_stix_import_rejects_invalid_filter_definitions(
    client: TestClient,
    auth_headers: dict[str, str],
    filters: dict[str, Any],
) -> None:
    response = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={"bundle": load_bundle("valid_bundle.json"), "filters": filters},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_analyst_promotes_an_accepted_outcome_to_audited_evidence(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    imported = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={"bundle": load_bundle("valid_bundle.json")},
        headers=auth_headers,
    )
    assert imported.status_code == 200
    import_id = imported.json()["import_id"]
    detail = client.get(
        f"/api/v1/intelligence/imports/{import_id}", headers=auth_headers
    )
    accepted = next(
        item for item in detail.json()["objects"] if item["disposition"] == "IMPORTED"
    )
    skipped = next(
        item for item in detail.json()["objects"] if item["disposition"] == "SKIPPED"
    )
    payload = {
        "polarity": "CONTEXTUAL",
        "claim": "The reviewed STIX indicator is relevant investigation context.",
        "uncertainty_notes": (
            "Provider presence does not establish attribution or current activity."
        ),
    }
    promoted = client.post(
        f"/api/v1/intelligence/imports/{import_id}/objects/{accepted['id']}/promote",
        json=payload,
        headers=auth_headers,
    )
    assert promoted.status_code == 200
    evidence = promoted.json()
    assert evidence["observation_id"] == accepted["observation_id"]
    assert evidence["polarity"] == "CONTEXTUAL"
    assert evidence["claim"] == payload["claim"]
    assert evidence["promoted_by"]
    assert evidence["analyst_reviewed_at"]

    refreshed = client.get(
        f"/api/v1/intelligence/imports/{import_id}", headers=auth_headers
    ).json()
    assert refreshed["promoted_objects"] == 1
    promoted_outcome = next(
        item for item in refreshed["objects"] if item["id"] == accepted["id"]
    )
    assert promoted_outcome["evidence_id"] == evidence["evidence_id"]

    promoted_history = client.get(
        "/api/v1/intelligence/imports?has_promotions=true", headers=auth_headers
    )
    assert promoted_history.status_code == 200
    assert promoted_history.json()["total"] == 1
    unpromoted_history = client.get(
        "/api/v1/intelligence/imports?has_promotions=false", headers=auth_headers
    )
    assert unpromoted_history.status_code == 200
    assert unpromoted_history.json()["total"] == 0

    detection = client.post(
        "/api/v1/detections",
        headers=auth_headers,
        json={
            "title": "Reviewed STIX indicator candidate",
            "kind": "SIGMA",
            "behavior_hypothesis": (
                "A monitored host communicates with the reviewed STIX indicator."
            ),
            "required_telemetry": ["DNS and network connection logs"],
            "candidate_logic": "title: Reviewed STIX indicator\nstatus: experimental",
            "supporting_evidence_ids": [evidence["evidence_id"]],
            "false_positives": ["Authorized security testing"],
            "limitations": ["Requires local telemetry validation"],
        },
    )
    assert detection.status_code == 201
    assert detection.json()["supporting_evidence_ids"] == [evidence["evidence_id"]]

    repeated = client.post(
        f"/api/v1/intelligence/imports/{import_id}/objects/{accepted['id']}/promote",
        json=payload,
        headers=auth_headers,
    )
    assert repeated.status_code == 409
    assert repeated.json()["detail"] == (
        "This import outcome has already been promoted to evidence"
    )
    invalid_outcome = client.post(
        f"/api/v1/intelligence/imports/{import_id}/objects/{skipped['id']}/promote",
        json=payload,
        headers=auth_headers,
    )
    assert invalid_outcome.status_code == 409

    audit = client.get("/api/v1/audit", headers=auth_headers)
    assert audit.status_code == 200
    promotion_audit = next(
        item
        for item in audit.json()
        if item["action"] == "intelligence.import_object_promoted"
    )
    assert promotion_audit["details"]["object_outcome_id"] == accepted["id"]


def test_import_history_filters_and_quarantines_object_outcomes(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with_issues = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={"bundle": load_bundle("valid_bundle.json")},
        headers=auth_headers,
    )
    assert with_issues.status_code == 200
    without_issues = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={
            "bundle": {
                "type": "bundle",
                "id": "bundle--bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "objects": [],
            }
        },
        headers=auth_headers,
    )
    assert without_issues.status_code == 200

    issue_history = client.get(
        "/api/v1/intelligence/imports?has_issues=true", headers=auth_headers
    )
    assert issue_history.status_code == 200
    assert issue_history.json()["total"] == 1
    assert issue_history.json()["items"][0]["status"] == "COMPLETED_WITH_ISSUES"
    assert issue_history.json()["items"][0]["skipped_objects"] == 1

    clean_history = client.get(
        "/api/v1/intelligence/imports?has_issues=false", headers=auth_headers
    )
    assert clean_history.status_code == 200
    assert clean_history.json()["total"] == 1
    assert clean_history.json()["items"][0]["status"] == "COMPLETED"

    completed_history = client.get(
        "/api/v1/intelligence/imports?status=COMPLETED", headers=auth_headers
    )
    assert completed_history.status_code == 200
    assert completed_history.json()["total"] == 1
    assert completed_history.json()["items"][0]["id"] == without_issues.json()["import_id"]

    detail = client.get(
        f"/api/v1/intelligence/imports/{with_issues.json()['import_id']}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["bundle_hash"]
    assert payload["contract"]["format"] == "STIX_2_1"
    assert len(payload["objects"]) == 3
    quarantined = next(
        item for item in payload["objects"] if item["disposition"] == "SKIPPED"
    )
    assert quarantined["code"] == "UNSUPPORTED_OBJECT_TYPE"
    assert quarantined["raw_record"]["type"] == "relationship"
    accepted = next(item for item in payload["objects"] if item["disposition"] == "IMPORTED")
    assert accepted["entity_id"]
    assert accepted["observation_id"]
    assert accepted["raw_record"] == {}

    missing = client.get(
        "/api/v1/intelligence/imports/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        headers=auth_headers,
    )
    assert missing.status_code == 404

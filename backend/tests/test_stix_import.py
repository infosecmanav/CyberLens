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
    assert payload["source_id"] == "manual-stix-2-1"
    assert payload["received_objects"] == 3
    assert payload["accepted_objects"] == 2
    assert payload["imported_observations"] == 2
    assert payload["created_entities"] == 2
    assert payload["skipped_objects"] == 1
    assert payload["rejected_objects"] == 0
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

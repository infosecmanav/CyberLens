import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.intelligence.export import (
    ExportValidationError,
    bundle_hash,
    validate_frozen_bundle,
)
from app.intelligence.taxii import TaxiiCollectionDocument, TaxiiPollResult
from app.models import TaxiiCollection, TaxiiExportPolicy, TaxiiServer

STIX_FIXTURES = Path(__file__).parent / "fixtures" / "stix"
MARKING_ID = "marking-definition--bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


class WritableTaxiiClient:
    def __init__(self) -> None:
        self.deliveries: list[list[dict[str, Any]]] = []

    async def discover(
        self, server: TaxiiServer
    ) -> tuple[str, list[TaxiiCollectionDocument]]:
        del server
        return (
            "https://taxii.example.test/api/",
            [
                TaxiiCollectionDocument(
                    collection_id="sharing",
                    title="Approved sharing",
                    description="Sanitized write fixture",
                    can_read=True,
                    can_write=True,
                    media_types=["application/stix+json;version=2.1"],
                )
            ],
        )

    async def poll(
        self, server: TaxiiServer, collection: TaxiiCollection
    ) -> TaxiiPollResult:
        del server, collection
        return TaxiiPollResult(pages=[[]], manifest_objects=0, cursor=None)

    async def send_objects(
        self,
        server: TaxiiServer,
        collection: TaxiiCollection,
        objects: list[dict[str, Any]],
    ) -> dict[str, object]:
        del server, collection
        self.deliveries.append(objects)
        return {
            "http_status": 202,
            "id": "status--11111111-1111-4111-8111-111111111111",
            "status": "complete",
            "success_count": len(objects),
        }


def analyst_headers(client: TestClient) -> dict[str, str]:
    email = "analyst@example.com"
    password = "correct horse battery staple"
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "Export Analyst", "password": password},
    )
    assert registration.status_code == 201
    token = client.post(
        "/api/v1/auth/token", data={"username": email, "password": password}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def promoted_marked_evidence(client: TestClient, headers: dict[str, str]) -> str:
    bundle = json.loads((STIX_FIXTURES / "valid_bundle.json").read_text())
    bundle["objects"] = [
        bundle["objects"][0],
        {
            "type": "marking-definition",
            "spec_version": "2.1",
            "id": MARKING_ID,
            "created": "2026-10-20T09:00:00Z",
            "definition_type": "statement",
            "definition": {"statement": "Fixture sharing policy"},
        },
    ]
    imported = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        headers=headers,
        json={"bundle": bundle},
    )
    assert imported.status_code == 200
    detail = client.get(
        f"/api/v1/intelligence/imports/{imported.json()['import_id']}", headers=headers
    ).json()
    accepted = next(item for item in detail["objects"] if item["disposition"] == "IMPORTED")
    promoted = client.post(
        f"/api/v1/intelligence/imports/{imported.json()['import_id']}/objects/"
        f"{accepted['id']}/promote",
        headers=headers,
        json={
            "polarity": "SUPPORTS",
            "claim": "Reviewed indicator is approved for controlled sharing.",
            "uncertainty_notes": "Sharing does not establish attribution or current activity.",
        },
    )
    assert promoted.status_code == 200
    return promoted.json()["evidence_id"]


def writable_collection(
    client: TestClient, headers: dict[str, str], taxii: WritableTaxiiClient
) -> str:
    client.app.state.taxii_client = taxii
    server = client.post(
        "/api/v1/taxii/servers",
        headers=headers,
        json={
            "name": "Approved exchange",
            "discovery_url": "https://taxii.example.test/taxii2/",
        },
    ).json()
    discovered = client.post(
        f"/api/v1/taxii/servers/{server['id']}/discover", headers=headers
    )
    assert discovered.status_code == 200
    return discovered.json()["collections"][0]["id"]


def test_controlled_export_requires_allowlist_independent_approval_and_write_auth(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    analyst = analyst_headers(client)
    evidence_id = promoted_marked_evidence(client, analyst)
    taxii = WritableTaxiiClient()
    collection_id = writable_collection(client, auth_headers, taxii)
    created = client.post(
        "/api/v1/exports/policies",
        headers=auth_headers,
        json={
            "name": "Marked partner sharing",
            "collection_id": collection_id,
            "allowed_marking_refs": [MARKING_ID],
            "max_objects": 10,
        },
    )
    assert created.status_code == 201
    policy = created.json()
    assert policy["enabled"] is False
    assert policy["require_approval"] is True

    request_body = {
        "policy_id": policy["id"],
        "evidence_ids": [evidence_id],
        "risk_summary": "Share one reviewed and marked indicator with the approved partner.",
    }
    assert client.post(
        "/api/v1/exports/requests", headers=analyst, json=request_body
    ).status_code == 409

    enabled = client.put(
        f"/api/v1/exports/policies/{policy['id']}",
        headers=auth_headers,
        json={
            "enabled": True,
            "allowed_marking_refs": [MARKING_ID],
            "allow_unmarked": False,
            "max_objects": 10,
        },
    )
    assert enabled.status_code == 200

    eligible = client.get(
        f"/api/v1/exports/eligible-evidence?policy_id={policy['id']}", headers=analyst
    )
    assert eligible.status_code == 200
    assert eligible.json()[0]["evidence_id"] == evidence_id
    assert eligible.json()[0]["eligible"] is True

    requested = client.post(
        "/api/v1/exports/requests", headers=analyst, json=request_body
    )
    assert requested.status_code == 201
    export = requested.json()
    assert export["status"] == "PENDING_APPROVAL"
    assert export["object_count"] == 1
    assert export["bundle_hash"]
    assert [item["type"] for item in export["stix_bundle"]["objects"]] == [
        "marking-definition",
        "indicator",
    ]
    assert export["stix_bundle"]["objects"][1]["object_marking_refs"] == [MARKING_ID]

    assert client.post(
        f"/api/v1/exports/requests/{export['id']}/deliver", headers=analyst
    ).status_code == 409
    assert client.post(
        f"/api/v1/exports/requests/{export['id']}/resolve",
        headers=analyst,
        json={
            "status": "APPROVED",
            "rationale": "The destination and markings were independently reviewed.",
        },
    ).status_code == 403

    approved = client.post(
        f"/api/v1/exports/requests/{export['id']}/resolve",
        headers=auth_headers,
        json={
            "status": "APPROVED",
            "rationale": "The destination and markings were independently reviewed.",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"

    delivered = client.post(
        f"/api/v1/exports/requests/{export['id']}/deliver", headers=analyst
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "DELIVERED"
    assert delivered.json()["delivery_attempts"] == 1
    assert delivered.json()["delivery_receipt"]["http_status"] == 202
    assert len(taxii.deliveries) == 1
    assert taxii.deliveries[0][1]["id"] == "indicator--22222222-2222-4222-8222-222222222222"
    assert client.post(
        f"/api/v1/exports/requests/{export['id']}/deliver", headers=analyst
    ).status_code == 409

    history = client.get("/api/v1/exports/requests", headers=analyst)
    assert history.status_code == 200
    assert history.json()[0]["bundle_hash"] == export["bundle_hash"]
    audit = client.get("/api/v1/audit", headers=auth_headers).json()
    actions = {item["action"] for item in audit}
    assert {"export.requested", "export.approval_resolved", "export.delivered"} <= actions


def test_export_rejects_markings_outside_destination_policy(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    analyst = analyst_headers(client)
    evidence_id = promoted_marked_evidence(client, analyst)
    collection_id = writable_collection(client, auth_headers, WritableTaxiiClient())
    other_marking = "marking-definition--cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    policy = client.post(
        "/api/v1/exports/policies",
        headers=auth_headers,
        json={
            "name": "Different marking",
            "collection_id": collection_id,
            "allowed_marking_refs": [other_marking],
        },
    ).json()
    client.put(
        f"/api/v1/exports/policies/{policy['id']}",
        headers=auth_headers,
        json={
            "enabled": True,
            "allowed_marking_refs": [other_marking],
            "allow_unmarked": False,
            "max_objects": 100,
        },
    )
    response = client.post(
        "/api/v1/exports/requests",
        headers=analyst,
        json={
            "policy_id": policy["id"],
            "evidence_ids": [evidence_id],
            "risk_summary": "Attempt sharing under a mismatched marking allowlist.",
        },
    )
    assert response.status_code == 409
    assert "outside the destination allowlist" in response.json()["detail"]


def test_export_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/exports/policies").status_code == 401
    assert client.get("/api/v1/exports/requests").status_code == 401
    assert client.post("/api/v1/exports/requests", json={}).status_code == 401


def test_frozen_export_is_rechecked_against_current_hash_and_marking_policy() -> None:
    indicator = {
        "type": "indicator",
        "spec_version": "2.1",
        "id": "indicator--22222222-2222-4222-8222-222222222222",
        "object_marking_refs": [MARKING_ID],
    }
    bundle: dict[str, object] = {
        "type": "bundle",
        "id": "bundle--11111111-1111-4111-8111-111111111111",
        "objects": [indicator],
    }
    digest = bundle_hash(bundle)
    policy = TaxiiExportPolicy(
        name="Fixture",
        allowed_marking_refs=[MARKING_ID],
        allow_unmarked=False,
        max_objects=10,
        require_approval=True,
    )
    assert validate_frozen_bundle(bundle, digest, policy) == [indicator]

    policy.allowed_marking_refs = []
    with pytest.raises(ExportValidationError, match="no longer allows"):
        validate_frozen_bundle(bundle, digest, policy)
    policy.allowed_marking_refs = [MARKING_ID]
    indicator["labels"] = ["tampered-after-approval"]
    with pytest.raises(ExportValidationError, match="hash"):
        validate_frozen_bundle(bundle, digest, policy)

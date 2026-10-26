from fastapi.testclient import TestClient

from app.intelligence.connectors.base import BaseIntelligenceConnector
from app.intelligence.connectors.models import (
    ConnectorCapability,
    ConnectorManifest,
    ConnectorOutcome,
    ConnectorRequest,
    ConnectorResult,
)


class OfflineDomainConnector(BaseIntelligenceConnector):
    manifest = ConnectorManifest(
        source_id="offline-domain-fixture",
        name="Offline domain fixture",
        capabilities=[ConnectorCapability(operation="lookup", entity_types={"DOMAIN"})],
    )

    def __init__(self, source_id: str) -> None:
        self.manifest = self.manifest.model_copy(update={"source_id": source_id})

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        del request
        return ConnectorResult(
            source_id=self.manifest.source_id,
            outcome=ConnectorOutcome.NO_RESULT,
            message="Hermetic monitoring fixture",
        )


def lookup_demo_entity(
    client: TestClient, headers: dict[str, str], value: str = "example.test"
) -> dict[str, object]:
    response = client.post(
        "/api/v1/intelligence/lookup",
        headers=headers,
        json={"value": value, "source_ids": ["local-fixtures"], "include_demo": True},
    )
    assert response.status_code == 200
    return response.json()


def create_completed_investigation(
    client: TestClient, headers: dict[str, str]
) -> dict[str, object]:
    created = client.post(
        "/api/v1/investigations",
        headers=headers,
        json={
            "title": "Detection evidence review",
            "objective": "Collect explicit evidence for a draft detection workflow.",
            "seed_value": "example.test",
            "source_ids": ["local-fixtures"],
            "include_demo": True,
        },
    ).json()
    return client.post(
        f"/api/v1/investigations/{created['id']}/run", headers=headers
    ).json()


def test_evidence_backed_graph_and_detection_validation(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    investigation = create_completed_investigation(client, auth_headers)
    evidence = client.get(
        f"/api/v1/investigations/{investigation['id']}/evidence"
    ).json()[0]
    target = lookup_demo_entity(client, auth_headers, "related.test")["entity"]
    relation = client.post(
        "/api/v1/graph/relationships",
        headers=auth_headers,
        json={
            "source_entity_id": investigation["seed_entity_id"],
            "target_entity_id": target["id"],
            "relationship_type": "RESOLVES_TOGETHER_IN_TEST",
            "evidence_id": evidence["id"],
            "confidence": 0.5,
            "provenance": {"mode": "test-fixture"},
            "uncertainty_notes": "This relationship exists only for integration testing.",
            "first_seen": "2026-10-24T12:00:00Z",
            "last_seen": "2026-10-24T12:05:00Z",
        },
    )
    assert relation.status_code == 201
    assert relation.json()["first_seen"] == "2026-10-24T12:00:00Z"
    graph = client.get(f"/api/v1/investigations/{investigation['id']}/graph")
    assert graph.status_code == 200
    assert len(graph.json()["nodes"]) == 2
    assert graph.json()["edges"][0]["evidence_id"] == evidence["id"]

    detection = client.post(
        "/api/v1/detections",
        headers=auth_headers,
        json={
            "title": "Demonstration DNS candidate",
            "kind": "SIGMA",
            "investigation_id": investigation["id"],
            "finding_id": investigation["findings"][0]["id"],
            "behavior_hypothesis": (
                "A monitored host resolves a domain identified by reviewed evidence."
            ),
            "technique_ids": ["T1071.004"],
            "required_telemetry": ["DNS query logs"],
            "field_assumptions": {"query": "dns.question.name"},
            "candidate_logic": "title: Demonstration only\nstatus: experimental",
            "supporting_evidence_ids": [evidence["id"]],
            "false_positives": ["Authorized testing"],
            "limitations": ["Fixture-backed and not suitable for production"],
        },
    )
    assert detection.status_code == 201
    assert detection.json()["validation_status"] == "NEEDS_VALIDATION"
    production_without_evidence = client.post(
        f"/api/v1/detections/{detection.json()['id']}/validations",
        headers=auth_headers,
        json={
            "status": "VALIDATED_IN_PRODUCTION",
            "environment": "production",
            "validation_evidence": {},
            "notes": "No actual evidence exists for this attempted state.",
        },
    )
    assert production_without_evidence.status_code == 422
    validated = client.post(
        f"/api/v1/detections/{detection.json()['id']}/validations",
        headers=auth_headers,
        json={
            "status": "VALIDATED_IN_TEST",
            "environment": "isolated-test",
            "validation_evidence": {"matched_events": 1, "fixture": True},
            "notes": "Validated only against an isolated fixture event.",
        },
    )
    assert validated.status_code == 200
    assert validated.json()["validation_status"] == "VALIDATED_IN_TEST"


def test_case_approval_playbook_and_dry_run_controls(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    item_case = client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={"title": "IOC review case", "summary": "Track review tasks.", "priority": "HIGH"},
    )
    assert item_case.status_code == 201
    task = client.post(
        f"/api/v1/cases/{item_case.json()['id']}/tasks",
        headers=auth_headers,
        json={
            "title": "Block test address",
            "description": "Simulate a high-impact response action.",
            "action_type": "BLOCK_IP",
            "high_impact": True,
        },
    )
    assert task.status_code == 201
    blocked = client.post(
        f"/api/v1/cases/tasks/{task.json()['id']}/execute", headers=auth_headers
    )
    assert blocked.status_code == 409
    approval = client.post(
        f"/api/v1/cases/tasks/{task.json()['id']}/approval",
        headers=auth_headers,
        json={"risk_summary": "Blocking an address could disrupt legitimate network activity."},
    )
    assert approval.status_code == 200
    resolved = client.post(
        f"/api/v1/cases/approvals/{approval.json()['id']}/resolve",
        headers=auth_headers,
        json={"status": "APPROVED", "rationale": "Approved for dry-run validation only."},
    )
    assert resolved.status_code == 200
    executed = client.post(
        f"/api/v1/cases/tasks/{task.json()['id']}/execute", headers=auth_headers
    )
    assert executed.status_code == 200
    assert executed.json()["dry_run"] is True
    assert executed.json()["status"] == "COMPLETED"

    playbooks = client.get("/api/v1/playbooks")
    assert playbooks.status_code == 200
    assert len(playbooks.json()) == 9
    execution = client.post(
        f"/api/v1/playbooks/{playbooks.json()[0]['id']}/executions",
        headers=auth_headers,
        json={"case_id": item_case.json()["id"], "dry_run": True},
    )
    assert execution.status_code == 201
    assert execution.json()["status"] == "COMPLETED"
    assert all(event["external_action_performed"] is False for event in execution.json()["events"])


def test_monitoring_baseline_duplicate_and_material_change(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    registry = client.app.state.connector_manager.registry
    for source_id in ("crt-sh", "rdap"):
        registry._connectors[source_id] = OfflineDomainConnector(source_id)  # noqa: SLF001
    seed = lookup_demo_entity(client, auth_headers)["entity"]
    target = lookup_demo_entity(client, auth_headers, "target.test")["entity"]
    objective = client.post(
        "/api/v1/monitoring",
        headers=auth_headers,
        json={
            "name": "Example domain monitor",
            "objective": "Track source-backed changes for the example domain.",
            "entity_id": seed["id"],
            "cadence_minutes": 15,
        },
    )
    assert objective.status_code == 201
    first = client.post(
        f"/api/v1/monitoring/{objective.json()['id']}/run", headers=auth_headers
    )
    second = client.post(
        f"/api/v1/monitoring/{objective.json()['id']}/run", headers=auth_headers
    )
    assert first.status_code == 200
    assert second.status_code == 200
    changes = client.get("/api/v1/monitoring/changes").json()
    assert changes[0]["change_type"] == "NO_MATERIAL_CHANGE"
    assert changes[1]["change_type"] == "BASELINE"

    relationship = client.post(
        "/api/v1/graph/relationships",
        headers=auth_headers,
        json={
            "source_entity_id": seed["id"],
            "target_entity_id": target["id"],
            "relationship_type": "RELATED_FOR_MONITORING_TEST",
            "provenance": {"fixture": True},
            "uncertainty_notes": "Created to verify material change detection.",
        },
    )
    assert relationship.status_code == 201
    third = client.post(
        f"/api/v1/monitoring/{objective.json()['id']}/run", headers=auth_headers
    )
    assert third.status_code == 200
    material = client.get("/api/v1/monitoring/changes?actionable_only=true").json()
    assert material[0]["change_type"] == "NEW_RELATIONSHIP"
    assert material[0]["is_actionable"] is True
    acknowledged = client.post(
        f"/api/v1/monitoring/changes/{material[0]['id']}/acknowledge",
        headers=auth_headers,
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged_at"] is not None

    metrics = client.get("/api/v1/operations/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["demonstration_records"] == 2
    audit = client.get("/api/v1/audit", headers=auth_headers)
    assert audit.status_code == 200
    assert any(event["action"] == "INTELLIGENCE_CHANGE_ACKNOWLEDGED" for event in audit.json())

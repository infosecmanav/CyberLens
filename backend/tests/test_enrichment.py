import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.intelligence.connectors.base import BaseIntelligenceConnector
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.connectors.models import (
    ConnectorCapability,
    ConnectorManifest,
    ConnectorOutcome,
    ConnectorRequest,
    ConnectorResult,
    IntelligenceEntity,
    NormalizedObservation,
)
from app.intelligence.connectors.registry import ConnectorRegistry

STIX_FIXTURES = Path(__file__).parent / "fixtures" / "stix"


class DomainEnrichmentConnector(BaseIntelligenceConnector):
    manifest = ConnectorManifest(
        source_id="osv",
        name="Sanitized enrichment fixture",
        capabilities=[ConnectorCapability(operation="lookup", entity_types={"DOMAIN"})],
        active_requests_allowed=False,
    )

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        assert request.entity is not None
        return ConnectorResult(
            source_id="osv",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference="https://osv.dev/fixture",
            observations=[
                NormalizedObservation(
                    entity=IntelligenceEntity(
                        entity_type=request.entity.entity_type,
                        value=request.entity.value,
                    ),
                    observation_type="FIXTURE_ENRICHMENT",
                    summary="Fixture enrichment for the imported domain.",
                    observed_at=datetime(2026, 10, 25, 16, tzinfo=UTC),
                    source_reference="https://osv.dev/fixture/record",
                    attributes={"fixture": True, "verdict": None},
                    raw_record={"id": "fixture-enrichment-1"},
                    external_id="fixture-enrichment-1",
                )
            ],
        )


class NoResultDomainConnector(DomainEnrichmentConnector):
    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        del request
        return ConnectorResult(source_id="osv", outcome=ConnectorOutcome.NO_RESULT)


def manager(connector: BaseIntelligenceConnector) -> ConnectorManager:
    registry = ConnectorRegistry()
    registry.register(connector)
    return ConnectorManager(registry)


def import_domain(client: TestClient, auth_headers: dict[str, str]) -> str:
    bundle = json.loads((STIX_FIXTURES / "valid_bundle.json").read_text())
    bundle["objects"] = [bundle["objects"][0]]
    response = client.post(
        "/api/v1/intelligence/imports/stix-bundles",
        json={"bundle": bundle},
        headers=auth_headers,
    )
    assert response.status_code == 200
    return response.json()["items"][0]["entity_id"]


def create_policy(
    client: TestClient, auth_headers: dict[str, str], name: str = "Imported domain context"
) -> dict[str, object]:
    response = client.post(
        "/api/v1/enrichment/policies",
        headers=auth_headers,
        json={
            "name": name,
            "entity_types": ["DOMAIN"],
            "source_ids": ["osv"],
            "max_entities_per_run": 10,
            "cadence_minutes": 60,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_enrichment_policy_processes_new_entities_once_with_full_lineage(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    entity_id = import_domain(client, auth_headers)
    client.app.state.connector_manager = manager(DomainEnrichmentConnector())
    policy = create_policy(client, auth_headers)
    assert policy["entity_types"] == ["DOMAIN"]
    assert policy["source_ids"] == ["osv"]
    assert policy["enabled"] is True

    response = client.post(
        f"/api/v1/enrichment/policies/{policy['id']}/run", headers=auth_headers
    )
    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "COMPLETED"
    assert run["candidate_entities"] == 1
    assert run["processed_entities"] == 1
    assert run["new_observations"] == 1
    assert run["source_outcomes"] == {"SUCCESS": 1}
    assert run["items"][0]["entity_id"] == entity_id
    assert run["items"][0]["new_observation_ids"]
    assert run["items"][0]["source_outcomes"][0]["source_id"] == "osv"

    observations = client.get(f"/api/v1/intelligence/entities/{entity_id}/observations")
    assert observations.status_code == 200
    enriched = next(
        item for item in observations.json() if item["observation_type"] == "FIXTURE_ENRICHMENT"
    )
    assert enriched["source_id"] == "osv"
    assert enriched["attributes"]["verdict"] is None

    repeated = client.post(
        f"/api/v1/enrichment/policies/{policy['id']}/run", headers=auth_headers
    )
    assert repeated.status_code == 200
    assert repeated.json()["candidate_entities"] == 0
    assert repeated.json()["new_observations"] == 0

    history = client.get("/api/v1/enrichment/runs", headers=auth_headers)
    assert history.status_code == 200
    assert len(history.json()) == 2


def test_no_result_is_recorded_without_creating_an_observation_or_verdict(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    entity_id = import_domain(client, auth_headers)
    before = client.get(f"/api/v1/intelligence/entities/{entity_id}/observations").json()
    client.app.state.connector_manager = manager(NoResultDomainConnector())
    policy = create_policy(client, auth_headers, "No result policy")
    run = client.post(
        f"/api/v1/enrichment/policies/{policy['id']}/run", headers=auth_headers
    ).json()
    assert run["status"] == "COMPLETED"
    assert run["source_outcomes"] == {"NO_RESULT": 1}
    assert run["new_observations"] == 0
    assert run["items"][0]["observation_ids"] == []
    after = client.get(f"/api/v1/intelligence/entities/{entity_id}/observations").json()
    assert after == before


def test_enrichment_policy_rejects_demo_and_unknown_connectors(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    for source_id in ("local-fixtures", "missing-source"):
        response = client.post(
            "/api/v1/enrichment/policies",
            headers=auth_headers,
            json={
                "name": f"Rejected {source_id}",
                "entity_types": ["DOMAIN"],
                "source_ids": [source_id],
            },
        )
        assert response.status_code == 400


def test_enrichment_endpoints_require_admin_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/enrichment/policies").status_code == 401
    assert client.get("/api/v1/enrichment/runs").status_code == 401
    assert client.post(
        "/api/v1/enrichment/policies",
        json={
            "name": "Denied",
            "entity_types": ["DOMAIN"],
            "source_ids": ["osv"],
        },
    ).status_code == 401

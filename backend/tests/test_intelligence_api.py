from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.intelligence.connectors.base import BaseIntelligenceConnector
from app.intelligence.connectors.models import (
    ConnectorCapability,
    ConnectorManifest,
    ConnectorOutcome,
    ConnectorRequest,
    ConnectorResult,
    NormalizedObservation,
)


class QuotaExhaustedConnector(BaseIntelligenceConnector):
    manifest = ConnectorManifest(
        source_id="shodan",
        name="Quota fixture",
        capabilities=[ConnectorCapability(operation="lookup", entity_types={"DOMAIN"})],
    )

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        del request
        return ConnectorResult(
            source_id=self.manifest.source_id,
            outcome=ConnectorOutcome.QUOTA_EXHAUSTED,
            message="Fixture quota exhausted",
        )


class SharedUpstreamConnector(BaseIntelligenceConnector):
    manifest = ConnectorManifest(
        source_id="upstream-fixture",
        name="Upstream fixture",
        capabilities=[ConnectorCapability(operation="lookup", entity_types={"DOMAIN"})],
    )

    def __init__(self, source_id: str) -> None:
        self.manifest = ConnectorManifest(
            source_id=source_id,
            name=f"{source_id} fixture",
            capabilities=[ConnectorCapability(operation="lookup", entity_types={"DOMAIN"})],
        )

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        assert request.entity is not None
        return ConnectorResult(
            source_id=self.manifest.source_id,
            outcome=ConnectorOutcome.SUCCESS,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="SHARED_UPSTREAM_REPORT",
                    summary=f"{self.manifest.name} republishes the shared report.",
                    observed_at=datetime(2026, 10, 26, tzinfo=UTC),
                    source_reference="https://upstream.example.test/observations/42",
                    raw_record={"provider": self.manifest.source_id, "upstream_id": "42"},
                    external_id=f"{self.manifest.source_id}-42",
                )
            ],
        )


def test_normalize_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/intelligence/normalize",
        json={"value": " HTTPS://Example.COM:443/path#section "},
    )
    assert response.status_code == 200
    assert response.json()["entity_type"] == "URL"
    assert response.json()["normalized_value"] == "https://example.com/path"

    invalid = client.post("/api/v1/intelligence/normalize", json={"value": "not an IOC"})
    assert invalid.status_code == 422


def test_lookup_persists_and_deduplicates_entity_and_observation(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "value": " Example.TEST. ",
        "source_ids": ["local-fixtures"],
        "include_demo": True,
    }
    first = client.post("/api/v1/intelligence/lookup", json=payload, headers=auth_headers)
    second = client.post("/api/v1/intelligence/lookup", json=payload, headers=auth_headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "COMPLETED"
    assert first.json()["entity"]["normalized_value"] == "example.test"
    assert first.json()["entity"]["id"] == second.json()["entity"]["id"]
    assert first.json()["job_id"] != second.json()["job_id"]
    assert first.json()["results"][0]["outcome"] == "SUCCESS"
    assert first.json()["results"][0]["observation_ids"] == second.json()["results"][0][
        "observation_ids"
    ]

    entities = client.get("/api/v1/intelligence/entities")
    assert entities.status_code == 200
    assert entities.json()["total"] == 1
    entity_id = first.json()["entity"]["id"]
    observations = client.get(f"/api/v1/intelligence/entities/{entity_id}/observations")
    assert observations.status_code == 200
    assert len(observations.json()) == 1
    assert observations.json()[0]["attributes"]["demonstration"] is True


def test_lookup_rejects_unregistered_connector(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/intelligence/lookup",
        json={"value": "example.test", "source_ids": ["not-a-connector"]},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_lookup_keeps_success_when_virustotal_is_not_configured(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: object,
) -> None:
    monkeypatch.delenv("VIRUSTOTAL_API_KEY", raising=False)  # type: ignore[attr-defined]
    response = client.post(
        "/api/v1/intelligence/lookup",
        json={
            "value": "example.test",
            "source_ids": ["local-fixtures", "virustotal"],
            "include_demo": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PARTIAL"
    outcomes = {item["source_id"]: item for item in body["results"]}
    assert outcomes["virustotal"]["outcome"] == "NOT_CONFIGURED"
    assert outcomes["local-fixtures"]["outcome"] == "SUCCESS"
    assert len(outcomes["local-fixtures"]["observation_ids"]) == 1


def test_lookup_keeps_entity_and_observation_when_source_quota_is_exhausted(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    manager = client.app.state.connector_manager
    manager.registry._connectors["shodan"] = QuotaExhaustedConnector()  # noqa: SLF001
    response = client.post(
        "/api/v1/intelligence/lookup",
        json={
            "value": "example.test",
            "source_ids": ["local-fixtures", "shodan"],
            "include_demo": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PARTIAL"
    outcomes = {item["source_id"]: item for item in body["results"]}
    assert outcomes["shodan"]["outcome"] == "QUOTA_EXHAUSTED"
    assert outcomes["local-fixtures"]["outcome"] == "SUCCESS"
    entity_id = body["entity"]["id"]
    observations = client.get(f"/api/v1/intelligence/entities/{entity_id}/observations")
    assert observations.status_code == 200
    assert len(observations.json()) == 1


def test_misp_and_threatfox_records_retain_shared_upstream_provenance(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    registry = client.app.state.connector_manager.registry
    registry._connectors["misp"] = SharedUpstreamConnector("misp")  # noqa: SLF001
    registry._connectors["threatfox"] = SharedUpstreamConnector("threatfox")  # noqa: SLF001
    response = client.post(
        "/api/v1/intelligence/lookup",
        json={"value": "example.test", "source_ids": ["misp", "threatfox"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    observation_ids = {
        item["observation_ids"][0] for item in response.json()["results"]
    }
    assert len(observation_ids) == 2
    entity_id = response.json()["entity"]["id"]
    observations = client.get(
        f"/api/v1/intelligence/entities/{entity_id}/observations"
    ).json()
    assert {item["source_id"] for item in observations} == {"misp", "threatfox"}
    assert {item["source_reference"] for item in observations} == {
        "https://upstream.example.test/observations/42"
    }

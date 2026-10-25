from fastapi.testclient import TestClient


def test_source_catalog_is_seeded_and_truthful(client: TestClient) -> None:
    response = client.get("/api/v1/sources?limit=200")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 90

    sources = {item["source_id"]: item for item in payload["items"]}
    assert sources["local-fixtures"]["implementation_status"] == "IMPLEMENTED_AND_TESTED"
    assert sources["cisa-kev"]["implementation_status"] == "PUBLIC_FEED_SUPPORTED"
    assert sources["osv"]["implementation_status"] == "ADAPTER_SCAFFOLDED"
    assert sources["virustotal"]["implementation_status"] == "IMPLEMENTED_AWAITING_KEY"
    assert sources["virustotal"]["health_status"] == "UNKNOWN"
    assert sources["virustotal"]["environment_variables"] == ["VIRUSTOTAL_API_KEY"]


def test_source_detail_and_missing_source(client: TestClient) -> None:
    source = client.get("/api/v1/sources/virustotal")
    assert source.status_code == 200
    assert source.json()["free_access_status"] == "PUBLIC_API_TIER_RESTRICTED"
    assert source.json()["capabilities"][0]["operation"] == "lookup"

    missing = client.get("/api/v1/sources/not-real")
    assert missing.status_code == 404


def test_source_health_and_admin_connection_test(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    health = client.get("/api/v1/sources/virustotal/health")
    assert health.status_code == 200
    assert health.json()["required_environment_variables"] == ["VIRUSTOTAL_API_KEY"]
    assert health.json()["configured_environment_variables"] == []

    payload = {"entity_type": "DOMAIN", "value": "example.test"}
    assert client.post("/api/v1/sources/virustotal/test", json=payload).status_code == 401
    missing_key = client.post(
        "/api/v1/sources/virustotal/test", headers=auth_headers, json=payload
    )
    assert missing_key.status_code == 200
    assert missing_key.json()["outcome"] == "NOT_CONFIGURED"
    assert missing_key.json()["health_status"] == "NOT_CONFIGURED"

    fixture = client.post(
        "/api/v1/sources/local-fixtures/test", headers=auth_headers, json=payload
    )
    assert fixture.status_code == 200
    assert fixture.json()["outcome"] == "SUCCESS"
    assert fixture.json()["health_status"] == "HEALTHY"

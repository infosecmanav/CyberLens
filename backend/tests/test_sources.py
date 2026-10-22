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
    assert sources["virustotal"]["implementation_status"] == "INVESTIGATION_NEEDED"
    assert sources["virustotal"]["health_status"] == "UNKNOWN"
    assert sources["virustotal"]["environment_variables"] == ["VIRUSTOTAL_API_KEY"]


def test_source_detail_and_missing_source(client: TestClient) -> None:
    source = client.get("/api/v1/sources/virustotal")
    assert source.status_code == 200
    assert source.json()["free_access_status"] == "UNVERIFIED"
    assert source.json()["capabilities"] == []

    missing = client.get("/api/v1/sources/not-real")
    assert missing.status_code == 404

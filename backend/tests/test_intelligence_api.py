from fastapi.testclient import TestClient


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

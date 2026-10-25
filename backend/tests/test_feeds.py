import httpx
from fastapi.testclient import TestClient

from app.intelligence.connectors.vulnerability import CisaKevConnector


def _fixture_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "catalogVersion": "2026.10.25",
            "vulnerabilities": [
                {
                    "cveID": "CVE-2021-44228",
                    "vendorProject": "Apache",
                    "product": "Log4j2",
                    "vulnerabilityName": "Apache Log4j2 Remote Code Execution",
                    "dateAdded": "2021-12-10",
                    "dueDate": "2021-12-24",
                    "requiredAction": "Apply mitigations per vendor instructions.",
                    "knownRansomwareCampaignUse": "Known",
                }
            ],
        },
        request=request,
    )


def test_feed_subscription_run_deduplicates_and_can_pause(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    manager = client.app.state.connector_manager
    manager.registry._connectors["cisa-kev"] = CisaKevConnector(  # noqa: SLF001
        httpx.AsyncClient(transport=httpx.MockTransport(_fixture_response))
    )
    created = client.post(
        "/api/v1/feeds/subscriptions",
        headers=auth_headers,
        json={
            "name": "Official CISA KEV",
            "source_id": "cisa-kev",
            "cadence_minutes": 60,
            "max_records": 100,
        },
    )
    assert created.status_code == 201
    subscription = created.json()
    assert subscription["source_id"] == "cisa-kev"
    assert subscription["next_run_at"] is not None

    first = client.post(
        f"/api/v1/feeds/subscriptions/{subscription['id']}/run", headers=auth_headers
    )
    assert first.status_code == 200
    assert first.json()["status"] == "COMPLETED"
    assert first.json()["created_entities"] == 1
    assert first.json()["new_observations"] == 1
    assert first.json()["items"][0]["disposition"] == "IMPORTED"

    second = client.post(
        f"/api/v1/feeds/subscriptions/{subscription['id']}/run", headers=auth_headers
    )
    assert second.status_code == 200
    assert second.json()["reused_entities"] == 1
    assert second.json()["deduplicated_observations"] == 1
    assert second.json()["items"][0]["disposition"] == "DEDUPLICATED"

    paused = client.put(
        f"/api/v1/feeds/subscriptions/{subscription['id']}",
        headers=auth_headers,
        json={"enabled": False, "cadence_minutes": 120, "max_records": 50},
    )
    assert paused.status_code == 200
    assert paused.json()["next_run_at"] is None
    assert client.post(
        f"/api/v1/feeds/subscriptions/{subscription['id']}/run", headers=auth_headers
    ).status_code == 409

    runs = client.get("/api/v1/feeds/runs", headers=auth_headers)
    assert runs.status_code == 200
    assert len(runs.json()) == 2


def test_feed_subscription_rejects_unknown_sources_and_requires_admin(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "name": "Unsupported",
        "source_id": "osv",
        "cadence_minutes": 60,
        "max_records": 100,
    }
    assert client.post("/api/v1/feeds/subscriptions", json=payload).status_code == 401
    rejected = client.post(
        "/api/v1/feeds/subscriptions", headers=auth_headers, json=payload
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "Source does not expose an automated production feed"

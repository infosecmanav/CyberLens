import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.intelligence.taxii import (
    TaxiiClient,
    TaxiiCollectionDocument,
    TaxiiError,
    TaxiiPollResult,
)
from app.models import TaxiiCollection, TaxiiServer

FIXTURES = Path(__file__).parent / "fixtures" / "taxii"


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


def configured_server(**overrides: object) -> TaxiiServer:
    values: dict[str, object] = {
        "name": "Fixture server",
        "discovery_url": "https://taxii.example.test/taxii2/",
        "api_root_url": "https://taxii.example.test/api/",
        "timeout_seconds": 5,
        "page_size": 100,
        "max_pages": 3,
        "auth_environment_variable": None,
    }
    values.update(overrides)
    return TaxiiServer(**values)  # type: ignore[arg-type]


def readable_collection() -> TaxiiCollection:
    return TaxiiCollection(
        collection_id="malware-indicators",
        title="Malware indicators",
        can_read=True,
        can_write=False,
        selected=True,
        poll_interval_minutes=60,
    )


@pytest.mark.asyncio
async def test_taxii_21_discovery_manifest_and_paginated_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/taxii2/":
            return httpx.Response(200, json=fixture("discovery.json"))
        if request.url.path == "/api/collections/":
            return httpx.Response(200, json=fixture("collections.json"))
        if request.url.path.endswith("/manifest/"):
            return httpx.Response(200, json=fixture("manifest.json"))
        if request.url.params.get("next") == "opaque-page-2":
            return httpx.Response(200, json=fixture("objects_page_2.json"))
        return httpx.Response(200, json=fixture("objects_page_1.json"))

    monkeypatch.setenv("FIXTURE_TAXII_TOKEN", "secret-token")
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = TaxiiClient(http_client)
        server = configured_server(auth_environment_variable="FIXTURE_TAXII_TOKEN")
        api_root, collections = await client.discover(server)
        result = await client.poll(server, readable_collection())

    assert api_root == "https://taxii.example.test/api/"
    assert collections[0].collection_id == "malware-indicators"
    assert collections[0].can_read is True
    assert len(result.pages) == 2
    assert result.received_objects == 2
    assert result.manifest_objects == 1
    assert result.cursor == datetime(2026, 10, 25, 15, tzinfo=UTC)
    assert requests[-1].url.params["next"] == "opaque-page-2"
    assert all(request.headers["authorization"] == "Bearer secret-token" for request in requests)


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 429])
async def test_taxii_maps_relationship_and_rate_limit_failures(status_code: int) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, request=request))
    async with httpx.AsyncClient(transport=transport) as http_client:
        with pytest.raises(TaxiiError):
            await TaxiiClient(http_client).discover(configured_server())


@pytest.mark.asyncio
async def test_taxii_rejects_cross_authority_api_root() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"api_roots": ["https://untrusted.example/api/"]}, request=request
        )
    )
    async with httpx.AsyncClient(transport=transport) as http_client:
        with pytest.raises(TaxiiError, match="configured HTTPS authority"):
            await TaxiiClient(http_client).discover(configured_server())


@pytest.mark.asyncio
async def test_taxii_accepts_empty_collection_and_rejects_malformed_documents() -> None:
    def empty_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/manifest/"):
            return httpx.Response(200, json={"objects": [], "more": False}, request=request)
        return httpx.Response(200, json={"objects": [], "more": False}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(empty_handler)) as http_client:
        result = await TaxiiClient(http_client).poll(
            configured_server(), readable_collection()
        )
    assert result.received_objects == 0
    assert result.manifest_objects == 0

    malformed = httpx.MockTransport(
        lambda request: httpx.Response(200, content=b"not-json", request=request)
    )
    async with httpx.AsyncClient(transport=malformed) as http_client:
        with pytest.raises(TaxiiError, match="invalid JSON"):
            await TaxiiClient(http_client).discover(configured_server())


@pytest.mark.asyncio
async def test_taxii_stops_when_pagination_exceeds_the_configured_budget() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"objects": [], "more": True, "next": "still-more"},
            request=request,
        )

    server = configured_server(max_pages=1)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(TaxiiError, match="manifest exceeded"):
            await TaxiiClient(http_client).poll(server, readable_collection())


@pytest.mark.asyncio
async def test_taxii_21_object_delivery_uses_fixed_collection_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            202,
            json={"id": "status--fixture", "status": "pending", "pending_count": 1},
            request=request,
        )

    monkeypatch.setenv("FIXTURE_TAXII_TOKEN", "write-token")
    server = configured_server(auth_environment_variable="FIXTURE_TAXII_TOKEN")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        receipt = await TaxiiClient(http_client).send_objects(
            server,
            readable_collection(),
            [{"type": "indicator", "id": "indicator--fixture"}],
        )
    assert receipt == {
        "http_status": 202,
        "id": "status--fixture",
        "status": "pending",
        "pending_count": 1,
    }
    assert captured[0].url.path == "/api/collections/malware-indicators/objects/"
    assert captured[0].headers["authorization"] == "Bearer write-token"
    assert captured[0].headers["content-type"] == "application/taxii+json;version=2.1"


class StubTaxiiClient:
    async def discover(
        self, server: TaxiiServer
    ) -> tuple[str, list[TaxiiCollectionDocument]]:
        del server
        return (
            "https://taxii.example.test/api/",
            [
                TaxiiCollectionDocument(
                    collection_id="malware-indicators",
                    title="Malware indicators",
                    description="Sanitized fixture",
                    can_read=True,
                    can_write=False,
                    media_types=["application/stix+json;version=2.1"],
                )
            ],
        )

    async def poll(
        self, server: TaxiiServer, collection: TaxiiCollection
    ) -> TaxiiPollResult:
        del server, collection
        return TaxiiPollResult(
            pages=[fixture("objects_page_1.json")["objects"]],
            manifest_objects=1,
            cursor=datetime(2026, 10, 25, 15, tzinfo=UTC),
        )


def test_taxii_admin_configuration_discovery_and_import(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.app.state.taxii_client = StubTaxiiClient()
    created = client.post(
        "/api/v1/taxii/servers",
        headers=auth_headers,
        json={
            "name": "Partner exchange",
            "discovery_url": "https://taxii.example.test/taxii2/",
            "auth_environment_variable": "PARTNER_TAXII_TOKEN",
            "page_size": 100,
            "max_pages": 5,
        },
    )
    assert created.status_code == 201
    server = created.json()
    assert server["credential_configured"] is False
    assert "secret" not in server
    discovered = client.post(
        f"/api/v1/taxii/servers/{server['id']}/discover", headers=auth_headers
    )
    assert discovered.status_code == 200
    collection = discovered.json()["collections"][0]
    assert collection["can_read"] is True
    assert collection["can_write"] is False

    selected = client.put(
        f"/api/v1/taxii/collections/{collection['id']}",
        headers=auth_headers,
        json={"selected": True, "poll_interval_minutes": 30},
    )
    assert selected.status_code == 200
    run = client.post(
        f"/api/v1/taxii/collections/{collection['id']}/run", headers=auth_headers
    )
    assert run.status_code == 200
    assert run.json()["status"] == "COMPLETED"
    assert run.json()["received_objects"] == 1
    assert run.json()["accepted_objects"] == 1
    assert run.json()["cursor_completed_at"] == "2026-10-25T15:00:00Z"

    imports = client.get("/api/v1/intelligence/imports", headers=auth_headers)
    assert imports.status_code == 200
    assert imports.json()["items"][0]["source_id"] == "taxii-2-1"
    assert imports.json()["items"][0]["source_reference"].endswith(
        "/collections/malware-indicators/objects/"
    )
    runs = client.get("/api/v1/taxii/runs", headers=auth_headers)
    assert runs.status_code == 200
    assert runs.json()[0]["import_ids"] == [imports.json()["items"][0]["id"]]

    duplicate_run = client.post(
        f"/api/v1/taxii/collections/{collection['id']}/run", headers=auth_headers
    )
    assert duplicate_run.status_code == 200
    duplicate_imports = client.get(
        "/api/v1/intelligence/imports", headers=auth_headers
    ).json()
    duplicate_import_id = duplicate_run.json()["import_ids"][0]
    duplicate_import = next(
        item for item in duplicate_imports["items"] if item["id"] == duplicate_import_id
    )
    assert duplicate_import["imported_observations"] == 0
    assert duplicate_import["deduplicated_observations"] == 1


def test_taxii_configuration_requires_admin_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/taxii/servers").status_code == 401
    assert client.post(
        "/api/v1/taxii/servers",
        json={"name": "Denied", "discovery_url": "https://taxii.example.test/taxii2/"},
    ).status_code == 401


@pytest.mark.parametrize(
    "url",
    [
        "http://taxii.example.test/taxii2/",
        "https://user:pass@taxii.example.test/taxii2/",
        "https://taxii.example.test/taxii2/?token=secret",
        "https://taxii.example.test/taxii2/#fragment",
        "https://localhost/taxii2/",
        "https://taxii.internal/taxii2/",
        "https://127.0.0.1/taxii2/",
        "https://10.0.0.4/taxii2/",
        "https://[::1]/taxii2/",
    ],
)
def test_taxii_configuration_rejects_unsafe_discovery_urls(
    client: TestClient, auth_headers: dict[str, str], url: str
) -> None:
    response = client.post(
        "/api/v1/taxii/servers",
        headers=auth_headers,
        json={"name": f"Unsafe {url}", "discovery_url": url},
    )
    assert response.status_code == 422

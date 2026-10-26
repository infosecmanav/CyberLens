from urllib.parse import parse_qs

import httpx

from app.intelligence.connectors.cti import (
    FeodoTrackerConnector,
    MalwareBazaarConnector,
    UrlhausConnector,
)
from app.intelligence.connectors.models import ConnectorRequest, IntelligenceEntity
from app.intelligence.connectors.url import OpenPhishConnector


def request(entity_type: str, value: str) -> ConnectorRequest:
    return ConnectorRequest(entity=IntelligenceEntity(entity_type=entity_type, value=value))


async def test_abuse_ch_connectors_report_shared_missing_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("ABUSECH_AUTH_KEY", raising=False)
    urlhaus = await UrlhausConnector().lookup(request("DOMAIN", "example.test"))
    bazaar = await MalwareBazaarConnector().lookup(request("SHA256", "a" * 64))
    assert urlhaus.outcome == "NOT_CONFIGURED"
    assert bazaar.outcome == "NOT_CONFIGURED"
    assert urlhaus.message == "ABUSECH_AUTH_KEY is not configured"
    assert bazaar.message == "ABUSECH_AUTH_KEY is not configured"


async def test_urlhaus_success_and_empty(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ABUSECH_AUTH_KEY", "fixture-key")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.headers["Auth-Key"] == "fixture-key"
        form = parse_qs(http_request.content.decode())
        if form.get("host") == ["empty.test"]:
            return httpx.Response(
                200, json={"query_status": "no_results"}, request=http_request
            )
        return httpx.Response(
            200,
            json={
                "query_status": "ok",
                "host": "example.test",
                "urlhaus_reference": "https://urlhaus.abuse.ch/host/example.test/",
                "urls": [{"id": "123", "url_status": "online"}],
                "tags": ["payload_delivery"],
                "date_added": "2026-10-25T10:00:00Z",
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = UrlhausConnector(client)
        success = await connector.lookup(request("DOMAIN", "example.test"))
        empty = await connector.lookup(request("DOMAIN", "empty.test"))
    assert success.outcome == "SUCCESS"
    assert success.observations[0].attributes["url_count"] == 1
    assert success.observations[0].attributes["tags"] == ["payload_delivery"]
    assert empty.outcome == "NO_RESULT"


async def test_malwarebazaar_hash_metadata_never_downloads_samples(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ABUSECH_AUTH_KEY", "fixture-key")
    sha256 = "a" * 64

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.method == "POST"
        assert http_request.headers["Auth-Key"] == "fixture-key"
        form = parse_qs(http_request.content.decode())
        assert form == {"query": ["get_info"], "hash": [sha256]}
        return httpx.Response(
            200,
            json={
                "query_status": "ok",
                "data": [
                    {
                        "sha256_hash": sha256,
                        "signature": "FixtureLoader",
                        "file_type": "exe",
                        "file_name": "fixture.exe",
                        "file_size": 1234,
                        "tags": ["loader"],
                        "first_seen": "2026-10-25T10:00:00Z",
                    }
                ],
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await MalwareBazaarConnector(client).lookup(request("SHA256", sha256))
    assert result.outcome == "SUCCESS"
    assert result.observations[0].attributes["signature"] == "FixtureLoader"
    assert result.observations[0].raw_record["file_name"] == "fixture.exe"


async def test_feodo_feed_is_bounded_and_quarantines_bad_records() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "ip_address": "203.0.113.10",
                    "port": 443,
                    "status": "online",
                    "malware": "Dridex",
                    "first_seen": "2026-10-20",
                    "last_online": "2026-10-25",
                },
                {"port": 8080, "malware": "Emotet"},
                {"ip_address": "203.0.113.11", "port": 8443, "malware": "QakBot"},
            ],
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await FeodoTrackerConnector(client).fetch_feed(ConnectorRequest(limit=2))
    assert result.outcome == "SUCCESS"
    assert len(result.observations) == 1
    assert result.observations[0].entity.value == "203.0.113.10"
    assert result.observations[0].attributes["malware"] == "Dridex"
    assert len(result.issues) == 1
    assert result.issues[0].code == "INVALID_FEODO_RECORD"
    assert result.message == "Feed was bounded to 2 records"


async def test_openphish_feed_is_bounded_and_quarantines_bad_urls() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                "https://phishing.example.test/login\n"
                "not-a-url\n"
                "http://second.example.test/path\n"
            ),
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenPhishConnector(client).fetch_feed(ConnectorRequest(limit=2))
    assert result.outcome == "SUCCESS"
    assert len(result.observations) == 1
    assert result.observations[0].entity.value == "https://phishing.example.test/login"
    assert result.observations[0].attributes["analyst_validation_required"] is True
    assert result.observations[0].raw_record == {
        "url": "https://phishing.example.test/login"
    }
    assert result.issues[0].code == "INVALID_OPENPHISH_RECORD"
    assert result.message == "Feed was bounded to 2 records"

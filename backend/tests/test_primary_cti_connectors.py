import json

import httpx

from app.intelligence.connectors.cti import (
    MispConnector,
    OtxConnector,
    ThreatFoxConnector,
    VirusTotalConnector,
)
from app.intelligence.connectors.knowledge import MitreAttackConnector
from app.intelligence.connectors.models import ConnectorRequest, IntelligenceEntity
from app.intelligence.connectors.vulnerability import CveOrgConnector


def request(entity_type: str, value: str) -> ConnectorRequest:
    return ConnectorRequest(entity=IntelligenceEntity(entity_type=entity_type, value=value))


async def test_credential_connectors_report_missing_configuration(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    names = [
        "VIRUSTOTAL_API_KEY",
        "OTX_API_KEY",
        "ABUSECH_AUTH_KEY",
        "MISP_URL",
        "MISP_API_KEY",
    ]
    for name in names:
        monkeypatch.delenv(name, raising=False)
    lookup = request("DOMAIN", "example.test")
    assert (await VirusTotalConnector().lookup(lookup)).outcome == "NOT_CONFIGURED"
    assert (await OtxConnector().lookup(lookup)).outcome == "NOT_CONFIGURED"
    assert (await ThreatFoxConnector().lookup(lookup)).outcome == "NOT_CONFIGURED"
    assert (await MispConnector().lookup(lookup)).outcome == "NOT_CONFIGURED"


async def test_virustotal_success_and_rate_limit(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("VIRUSTOTAL_API_KEY", "fixture-key")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.headers["x-apikey"] == "fixture-key"
        if http_request.url.path.endswith("limited.test"):
            return httpx.Response(429, headers={"retry-after": "60"}, request=http_request)
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "example.test",
                    "type": "domain",
                    "attributes": {
                        "last_analysis_date": 1_700_000_000,
                        "last_analysis_stats": {
                            "malicious": 3,
                            "suspicious": 1,
                            "harmless": 70,
                        },
                        "reputation": -5,
                        "tags": ["fixture"],
                    },
                }
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = VirusTotalConnector(client)
        success = await connector.lookup(request("DOMAIN", "example.test"))
        limited = await connector.lookup(request("DOMAIN", "limited.test"))
    assert success.outcome == "SUCCESS"
    assert success.observations[0].attributes["analysis_stats"]["malicious"] == 3
    assert success.observations[0].raw_record["id"] == "example.test"
    assert limited.outcome == "RATE_LIMITED"
    assert limited.retry_after_seconds == 60


async def test_otx_success_and_empty(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OTX_API_KEY", "fixture-key")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.headers["X-OTX-API-KEY"] == "fixture-key"
        count = 0 if "empty.test" in str(http_request.url) else 2
        return httpx.Response(
            200,
            json={
                "pulse_info": {
                    "count": count,
                    "pulses": [
                        {
                            "id": "pulse-1",
                            "name": "Fixture campaign",
                            "modified": "2026-10-25T10:00:00Z",
                        }
                    ] if count else [],
                },
                "validation": [],
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = OtxConnector(client)
        success = await connector.lookup(request("DOMAIN", "example.test"))
        empty = await connector.lookup(request("DOMAIN", "empty.test"))
    assert success.outcome == "SUCCESS"
    assert success.observations[0].attributes["pulse_count"] == 2
    assert empty.outcome == "NO_RESULT"


async def test_threatfox_success_and_malformed(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ABUSECH_AUTH_KEY", "fixture-key")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.headers["Auth-Key"] == "fixture-key"
        body = json.loads(http_request.content)
        assert body["query"] == "search_ioc"
        if body["search_term"] == "broken.test":
            return httpx.Response(200, json={"unexpected": True}, request=http_request)
        return httpx.Response(
            200,
            json={
                "query_status": "ok",
                "data": [
                    {
                        "id": "42",
                        "ioc_type": "domain",
                        "threat_type": "botnet_cc",
                        "malware": "win.fake",
                        "malware_printable": "Fixture malware",
                        "confidence_level": 80,
                        "last_seen": "2026-10-25 10:00:00",
                    }
                ],
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = ThreatFoxConnector(client)
        success = await connector.lookup(request("DOMAIN", "example.test"))
        malformed = await connector.lookup(request("DOMAIN", "broken.test"))
    assert success.outcome == "SUCCESS"
    assert success.observations[0].attributes["confidence_level"] == 80
    assert malformed.outcome == "PARSE_ERROR"


async def test_misp_success_and_private_url_rejection(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("MISP_URL", "https://misp.example.test")
    monkeypatch.setenv("MISP_API_KEY", "fixture-key")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.url.path == "/attributes/restSearch"
        assert http_request.headers["Authorization"] == "fixture-key"
        return httpx.Response(
            200,
            json={
                "response": {
                    "Attribute": [
                        {
                            "id": "17",
                            "uuid": "attribute-uuid",
                            "event_id": "8",
                            "type": "domain",
                            "category": "Network activity",
                            "timestamp": "1700000000",
                            "to_ids": True,
                        }
                    ]
                }
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        success = await MispConnector(client).lookup(request("DOMAIN", "example.test"))
    assert success.outcome == "SUCCESS"
    assert success.observations[0].attributes["event_id"] == "8"

    monkeypatch.setenv("MISP_URL", "https://127.0.0.1")
    rejected = await MispConnector().lookup(request("DOMAIN", "example.test"))
    assert rejected.outcome == "NOT_CONFIGURED"
    assert "private or reserved" in str(rejected.message)


async def test_cve_org_success_no_result_and_parse_error() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        if http_request.url.path.endswith("CVE-2099-9999"):
            return httpx.Response(404, request=http_request)
        if http_request.url.path.endswith("CVE-2099-9998"):
            return httpx.Response(200, json={"bad": True}, request=http_request)
        return httpx.Response(
            200,
            json={
                "cveMetadata": {
                    "cveId": "CVE-2021-44228",
                    "state": "PUBLISHED",
                    "datePublished": "2021-12-10T00:00:00Z",
                    "dateUpdated": "2026-10-25T00:00:00Z",
                    "assignerShortName": "apache",
                },
                "containers": {
                    "cna": {
                        "descriptions": [{"lang": "en", "value": "Log4Shell fixture"}],
                        "affected": [{"vendor": "Apache", "product": "Log4j2"}],
                    }
                },
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = CveOrgConnector(client)
        success = await connector.lookup(request("CVE", "CVE-2021-44228"))
        missing = await connector.lookup(request("CVE", "CVE-2099-9999"))
        malformed = await connector.lookup(request("CVE", "CVE-2099-9998"))
    assert success.outcome == "SUCCESS"
    assert success.observations[0].summary == "Log4Shell fixture"
    assert missing.outcome == "NO_RESULT"
    assert malformed.outcome == "PARSE_ERROR"


async def test_mitre_attack_lookup_uses_official_stix_shape() -> None:
    bundle = {
        "type": "bundle",
        "objects": [
            {
                "type": "attack-pattern",
                "id": "attack-pattern--fixture",
                "name": "Fixture technique",
                "description": "Technique description",
                "modified": "2026-10-25T10:00:00Z",
                "external_references": [
                    {"source_name": "mitre-attack", "external_id": "T1059.001"}
                ],
                "kill_chain_phases": [{"phase_name": "execution"}],
                "x_mitre_platforms": ["Windows"],
            }
        ],
    }

    def handler(http_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bundle, request=http_request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = MitreAttackConnector(client)
        success = await connector.lookup(request("ATTACK_TECHNIQUE", "T1059.001"))
        missing = await connector.lookup(request("ATTACK_TECHNIQUE", "T9999"))
    assert success.outcome == "SUCCESS"
    assert success.observations[0].attributes["platforms"] == ["Windows"]
    assert missing.outcome == "NO_RESULT"

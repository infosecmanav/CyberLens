import httpx

from app.intelligence.connectors.domain import CrtShConnector, RdapConnector
from app.intelligence.connectors.infrastructure import (
    CensysConnector,
    GreyNoiseConnector,
    ShodanConnector,
)
from app.intelligence.connectors.models import ConnectorRequest, IntelligenceEntity
from app.intelligence.connectors.reputation import AbuseIpDbConnector
from app.intelligence.connectors.url import UrlscanConnector


def request(entity_type: str, value: str) -> ConnectorRequest:
    return ConnectorRequest(entity=IntelligenceEntity(entity_type=entity_type, value=value))


async def test_keyed_infrastructure_connectors_report_missing_configuration(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    names = [
        "SHODAN_API_KEY",
        "CENSYS_API_TOKEN",
        "GREYNOISE_API_KEY",
        "ABUSEIPDB_API_KEY",
    ]
    for name in names:
        monkeypatch.delenv(name, raising=False)
    ip = request("IPV4", "203.0.113.10")
    assert (await ShodanConnector().lookup(ip)).outcome == "NOT_CONFIGURED"
    assert (await CensysConnector().lookup(ip)).outcome == "NOT_CONFIGURED"
    assert (await GreyNoiseConnector().lookup(ip)).outcome == "NOT_CONFIGURED"
    assert (await AbuseIpDbConnector().lookup(ip)).outcome == "NOT_CONFIGURED"


async def test_shodan_host_context(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SHODAN_API_KEY", "fixture-key")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.url.params["key"] == "fixture-key"
        return httpx.Response(
            200,
            json={
                "ip_str": "203.0.113.10",
                "ports": [80, 443],
                "hostnames": ["host.example.test"],
                "domains": ["example.test"],
                "asn": "AS64496",
                "org": "Fixture network",
                "country_code": "CA",
                "last_update": "2026-10-25T10:00:00Z",
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ShodanConnector(client).lookup(request("IPV4", "203.0.113.10"))
    assert result.outcome == "SUCCESS"
    assert result.observations[0].attributes["ports"] == [80, 443]
    assert result.observations[0].raw_record["asn"] == "AS64496"


async def test_censys_host_context_and_authorization(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CENSYS_API_TOKEN", "fixture-token")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.headers["Authorization"] == "Bearer fixture-token"
        return httpx.Response(
            200,
            json={
                "result": {
                    "resource": {
                        "ip": "203.0.113.10",
                        "last_updated_at": "2026-10-25T10:00:00Z",
                        "services": [{"port": 443, "service_name": "HTTP"}],
                        "dns": {"names": ["host.example.test"]},
                        "location": {"country": "Canada"},
                        "autonomous_system": {"asn": 64496},
                    }
                }
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await CensysConnector(client).lookup(request("IPV4", "203.0.113.10"))
    assert result.outcome == "SUCCESS"
    assert result.observations[0].attributes["services"][0]["port"] == 443


async def test_greynoise_scanner_context_is_not_a_verdict(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("GREYNOISE_API_KEY", "fixture-key")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.headers["key"] == "fixture-key"
        return httpx.Response(
            200,
            json={
                "ip": "203.0.113.10",
                "noise": True,
                "riot": False,
                "classification": "benign",
                "name": "Fixture scanner",
                "last_seen": "2026-10-25",
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await GreyNoiseConnector(client).lookup(request("IPV4", "203.0.113.10"))
    assert result.outcome == "SUCCESS"
    assert result.observations[0].observation_type == "INTERNET_SCANNER_CONTEXT"
    assert "scanner context" in result.observations[0].summary


async def test_abuseipdb_reputation_context(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ABUSEIPDB_API_KEY", "fixture-key")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.headers["Key"] == "fixture-key"
        assert http_request.url.params["maxAgeInDays"] == "90"
        return httpx.Response(
            200,
            json={
                "data": {
                    "ipAddress": "203.0.113.10",
                    "abuseConfidenceScore": 42,
                    "totalReports": 6,
                    "numDistinctUsers": 4,
                    "lastReportedAt": "2026-10-25T10:00:00Z",
                    "usageType": "Data Center/Web Hosting/Transit",
                    "isp": "Fixture ISP",
                    "countryCode": "CA",
                    "isTor": False,
                }
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await AbuseIpDbConnector(client).lookup(request("IPV4", "203.0.113.10"))
    assert result.outcome == "SUCCESS"
    assert result.observations[0].attributes["abuse_confidence_score"] == 42
    assert "analyst context" in result.observations[0].summary


async def test_rdap_domain_registration_context() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "objectClassName": "domain",
                "handle": "EXAMPLE-1",
                "ldhName": "example.test",
                "status": ["active"],
                "events": [
                    {"eventAction": "last changed", "eventDate": "2026-10-25T10:00:00Z"}
                ],
                "nameservers": [{"ldhName": "ns1.example.test"}],
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await RdapConnector(client).lookup(request("DOMAIN", "example.test"))
    assert result.outcome == "SUCCESS"
    assert result.observations[0].attributes["nameservers"] == ["ns1.example.test"]


async def test_crtsh_bounds_certificate_records_and_handles_empty() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        records = [] if http_request.url.params["q"] == "empty.test" else [
            {
                "id": index,
                "name_value": "example.test\nwww.example.test",
                "not_before": "2026-10-25T10:00:00Z",
            }
            for index in range(105)
        ]
        return httpx.Response(200, json=records, request=http_request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = CrtShConnector(client)
        result = await connector.lookup(request("DOMAIN", "example.test"))
        empty = await connector.lookup(request("DOMAIN", "empty.test"))
    assert result.outcome == "SUCCESS"
    assert result.observations[0].attributes["certificate_count"] == 105
    assert result.observations[0].attributes["bounded_records"] == 100
    assert result.observations[0].raw_record["truncated"] is True
    assert empty.outcome == "NO_RESULT"


async def test_urlscan_passive_search_never_submits(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("URLSCAN_API_KEY", "fixture-key")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.method == "GET"
        assert http_request.headers["api-key"] == "fixture-key"
        assert http_request.url.params["size"] == "20"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "task": {
                            "uuid": "scan-uuid",
                            "time": "2026-10-25T10:00:00Z",
                            "reportURL": "https://urlscan.io/result/scan-uuid/",
                        },
                        "page": {
                            "domain": "example.test",
                            "ip": "203.0.113.10",
                            "country": "CA",
                        },
                        "stats": {"uniqIPs": 1},
                    }
                ]
            },
            request=http_request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await UrlscanConnector(client).lookup(request("DOMAIN", "example.test"))
    assert result.outcome == "SUCCESS"
    assert result.observations[0].attributes["submission_enabled"] is False
    assert result.observations[0].external_id == "scan-uuid"

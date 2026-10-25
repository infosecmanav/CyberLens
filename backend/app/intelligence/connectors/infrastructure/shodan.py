import os
from typing import Any

import httpx

from app.intelligence.connectors.base import BaseIntelligenceConnector
from app.intelligence.connectors.http_support import http_error, parse_timestamp
from app.intelligence.connectors.models import (
    ConnectorCapability,
    ConnectorManifest,
    ConnectorOutcome,
    ConnectorRequest,
    ConnectorResult,
    NormalizedObservation,
)


class ShodanConnector(BaseIntelligenceConnector):
    api_root = "https://api.shodan.io/shodan/host"
    manifest = ConnectorManifest(
        source_id="shodan",
        name="Shodan Host API",
        capabilities=[
            ConnectorCapability(
                operation="lookup",
                entity_types={"IPV4", "IPV6"},
                requires_authentication=True,
            )
        ],
        required_environment_variables=["SHODAN_API_KEY"],
        default_timeout_seconds=15.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if request.entity is None or request.entity.entity_type not in {"IPV4", "IPV6"}:
            return self.not_supported("lookup for this entity type")
        key = os.getenv("SHODAN_API_KEY")
        if not key:
            return ConnectorResult(
                source_id="shodan",
                outcome=ConnectorOutcome.NOT_CONFIGURED,
                message="SHODAN_API_KEY is not configured",
            )
        url = f"{self.api_root}/{request.entity.value}"
        try:
            if self._client is not None:
                response = await self._client.get(url, params={"key": key, "minify": "true"})
            else:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(url, params={"key": key, "minify": "true"})
        except httpx.TimeoutException:
            return ConnectorResult(source_id="shodan", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="shodan", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("shodan", "Shodan", response)
        try:
            record: Any = response.json()
            if not isinstance(record, dict) or not isinstance(record.get("ip_str"), str):
                raise ValueError("Shodan response is missing ip_str")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="shodan", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        raw_ports = record.get("ports")
        ports: list[Any] = list(raw_ports) if isinstance(raw_ports, list) else []
        return ConnectorResult(
            source_id="shodan",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=url,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="INTERNET_EXPOSURE",
                    summary=f"Shodan reports {len(ports)} observed port(s) for this host.",
                    observed_at=parse_timestamp(record.get("last_update")),
                    source_reference=f"https://www.shodan.io/host/{request.entity.value}",
                    attributes={
                        "ports": ports[:100],
                        "hostnames": record.get("hostnames") or [],
                        "domains": record.get("domains") or [],
                        "asn": record.get("asn"),
                        "organization": record.get("org"),
                        "country_code": record.get("country_code"),
                    },
                    raw_record=record,
                    external_id=request.entity.value,
                )
            ],
        )

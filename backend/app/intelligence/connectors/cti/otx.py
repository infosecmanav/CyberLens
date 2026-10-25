import os
from typing import Any
from urllib.parse import quote

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


class OtxConnector(BaseIntelligenceConnector):
    api_root = "https://otx.alienvault.com/api/v1/indicators"
    manifest = ConnectorManifest(
        source_id="otx",
        name="LevelBlue OTX",
        capabilities=[
            ConnectorCapability(
                operation="lookup",
                entity_types={
                    "IPV4", "IPV6", "DOMAIN", "URL", "MD5", "SHA1", "SHA256", "CVE"
                },
                requires_authentication=True,
            )
        ],
        required_environment_variables=["OTX_API_KEY"],
        default_timeout_seconds=15.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def _get(self, url: str, api_key: str) -> httpx.Response:
        headers = {"X-OTX-API-KEY": api_key}
        if self._client is not None:
            return await self._client.get(url, headers=headers)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            return await client.get(url, headers=headers)

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if (
            request.entity is None
            or request.entity.entity_type not in self.manifest.capabilities[0].entity_types
        ):
            return self.not_supported("lookup for this entity type")
        api_key = os.getenv("OTX_API_KEY")
        if not api_key:
            return ConnectorResult(
                source_id="otx",
                outcome=ConnectorOutcome.NOT_CONFIGURED,
                message="OTX_API_KEY is not configured",
            )
        indicator_type = {
            "IPV4": "IPv4",
            "IPV6": "IPv6",
            "DOMAIN": "domain",
            "URL": "url",
            "MD5": "file",
            "SHA1": "file",
            "SHA256": "file",
            "CVE": "cve",
        }[request.entity.entity_type]
        url = f"{self.api_root}/{indicator_type}/{quote(request.entity.value, safe='')}/general"
        try:
            response = await self._get(url, api_key)
        except httpx.TimeoutException:
            return ConnectorResult(source_id="otx", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="otx", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("otx", "OTX", response)
        try:
            record: Any = response.json()
            pulse_info = record.get("pulse_info") if isinstance(record, dict) else None
            if not isinstance(record, dict) or not isinstance(pulse_info, dict):
                raise ValueError("OTX response is missing pulse_info")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="otx", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        count = int(pulse_info.get("count", 0))
        if count == 0:
            return ConnectorResult(
                source_id="otx",
                outcome=ConnectorOutcome.NO_RESULT,
                raw_reference=url,
                message="OTX returned no matching pulses",
            )
        pulses = pulse_info.get("pulses")
        latest = (
            pulses[0]
            if isinstance(pulses, list) and pulses and isinstance(pulses[0], dict)
            else {}
        )
        encoded_value = quote(request.entity.value, safe="")
        return ConnectorResult(
            source_id="otx",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=url,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="OTX_PULSE_CONTEXT",
                    summary=f"OTX associates this entity with {count} community pulse(s).",
                    observed_at=parse_timestamp(latest.get("modified")),
                    source_reference=(
                        f"https://otx.alienvault.com/indicator/{indicator_type}/{encoded_value}"
                    ),
                    attributes={
                        "pulse_count": count,
                        "latest_pulse_id": latest.get("id"),
                        "latest_pulse_name": latest.get("name"),
                        "validation": record.get("validation", []),
                    },
                    raw_record=record,
                    external_id=request.entity.value,
                )
            ],
        )

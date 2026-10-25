import base64
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


class VirusTotalConnector(BaseIntelligenceConnector):
    api_root = "https://www.virustotal.com/api/v3"
    manifest = ConnectorManifest(
        source_id="virustotal",
        name="VirusTotal API v3",
        capabilities=[
            ConnectorCapability(
                operation="lookup",
                entity_types={"IPV4", "IPV6", "DOMAIN", "URL", "MD5", "SHA1", "SHA256"},
                requires_authentication=True,
            )
        ],
        required_environment_variables=["VIRUSTOTAL_API_KEY"],
        default_timeout_seconds=15.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    def _path(self, entity_type: str, value: str) -> str:
        collection = {
            "IPV4": "ip_addresses",
            "IPV6": "ip_addresses",
            "DOMAIN": "domains",
            "MD5": "files",
            "SHA1": "files",
            "SHA256": "files",
        }.get(entity_type)
        if entity_type == "URL":
            identifier = base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")
            return f"{self.api_root}/urls/{identifier}"
        if collection is None:
            raise ValueError("Unsupported VirusTotal entity type")
        return f"{self.api_root}/{collection}/{value}"

    async def _get(self, url: str, api_key: str) -> httpx.Response:
        headers = {"x-apikey": api_key}
        if self._client is not None:
            return await self._client.get(url, headers=headers)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            return await client.get(url, headers=headers)

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if request.entity is None or not any(
            request.entity.entity_type in capability.entity_types
            for capability in self.manifest.capabilities
        ):
            return self.not_supported("lookup for this entity type")
        api_key = os.getenv("VIRUSTOTAL_API_KEY")
        if not api_key:
            return ConnectorResult(
                source_id="virustotal",
                outcome=ConnectorOutcome.NOT_CONFIGURED,
                message="VIRUSTOTAL_API_KEY is not configured",
            )
        url = self._path(request.entity.entity_type, request.entity.value)
        try:
            response = await self._get(url, api_key)
        except httpx.TimeoutException:
            return ConnectorResult(source_id="virustotal", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="virustotal",
                outcome=ConnectorOutcome.NETWORK_ERROR,
                message=str(exc),
            )
        if response.status_code != 200:
            return http_error("virustotal", "VirusTotal", response)
        try:
            payload: Any = response.json()
            record = payload.get("data") if isinstance(payload, dict) else None
            attributes = record.get("attributes") if isinstance(record, dict) else None
            if not isinstance(record, dict) or not isinstance(attributes, dict):
                raise ValueError("VirusTotal response is missing data attributes")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="virustotal", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        stats = attributes.get("last_analysis_stats")
        stats = stats if isinstance(stats, dict) else {}
        malicious = int(stats.get("malicious", 0))
        suspicious = int(stats.get("suspicious", 0))
        reference = (
            f"https://www.virustotal.com/gui/"
            f"{record.get('type', 'search')}/{record.get('id')}"
        )
        return ConnectorResult(
            source_id="virustotal",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=url,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="VIRUSTOTAL_REPUTATION",
                    summary=(
                        f"VirusTotal reports {malicious} malicious and {suspicious} suspicious "
                        "analysis results."
                    ),
                    observed_at=parse_timestamp(
                        attributes.get("last_analysis_date")
                        or attributes.get("last_modification_date")
                    ),
                    source_reference=reference,
                    attributes={
                        "analysis_stats": stats,
                        "reputation": attributes.get("reputation"),
                        "tags": list(attributes.get("tags", []))[:50]
                        if isinstance(attributes.get("tags"), list)
                        else [],
                    },
                    raw_record=record,
                    external_id=str(record.get("id") or request.entity.value),
                )
            ],
        )

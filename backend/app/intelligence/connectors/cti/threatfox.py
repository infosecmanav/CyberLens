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


class ThreatFoxConnector(BaseIntelligenceConnector):
    api_url = "https://threatfox-api.abuse.ch/api/v1/"
    manifest = ConnectorManifest(
        source_id="threatfox",
        name="ThreatFox",
        capabilities=[
            ConnectorCapability(
                operation="lookup",
                entity_types={"IPV4", "IPV6", "DOMAIN", "URL", "MD5", "SHA1", "SHA256"},
                requires_authentication=True,
            )
        ],
        required_environment_variables=["ABUSECH_AUTH_KEY"],
        default_timeout_seconds=15.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def _post(self, value: str, auth_key: str) -> httpx.Response:
        headers = {"Auth-Key": auth_key}
        body = {"query": "search_ioc", "search_term": value}
        if self._client is not None:
            return await self._client.post(self.api_url, headers=headers, json=body)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            return await client.post(self.api_url, headers=headers, json=body)

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if (
            request.entity is None
            or request.entity.entity_type not in self.manifest.capabilities[0].entity_types
        ):
            return self.not_supported("lookup for this entity type")
        auth_key = os.getenv("ABUSECH_AUTH_KEY")
        if not auth_key:
            return ConnectorResult(
                source_id="threatfox",
                outcome=ConnectorOutcome.NOT_CONFIGURED,
                message="ABUSECH_AUTH_KEY is not configured",
            )
        try:
            response = await self._post(request.entity.value, auth_key)
        except httpx.TimeoutException:
            return ConnectorResult(source_id="threatfox", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="threatfox", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("threatfox", "ThreatFox", response)
        try:
            payload: Any = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("query_status"), str):
                raise ValueError("ThreatFox response is missing query_status")
            query_status = payload["query_status"]
            if query_status in {"no_result", "no_results"}:
                return ConnectorResult(
                    source_id="threatfox",
                    outcome=ConnectorOutcome.NO_RESULT,
                    raw_reference=self.api_url,
                )
            records = payload.get("data")
            if query_status != "ok" or not isinstance(records, list):
                raise ValueError(f"ThreatFox returned {query_status}")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="threatfox", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        observations: list[NormalizedObservation] = []
        for record in records[:20]:
            if not isinstance(record, dict):
                continue
            malware = record.get("malware_printable") or record.get("malware") or "unknown malware"
            observations.append(
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="THREATFOX_IOC_MATCH",
                    summary=f"ThreatFox associates this indicator with {malware}.",
                    observed_at=parse_timestamp(
                        record.get("last_seen") or record.get("first_seen")
                    ),
                    source_reference=str(record.get("reference") or "https://threatfox.abuse.ch"),
                    attributes={
                        "ioc_type": record.get("ioc_type"),
                        "threat_type": record.get("threat_type"),
                        "malware": record.get("malware"),
                        "malware_printable": record.get("malware_printable"),
                        "confidence_level": record.get("confidence_level"),
                        "tags": record.get("tags") or [],
                    },
                    raw_record=record,
                    external_id=str(record.get("id") or request.entity.value),
                )
            )
        return ConnectorResult(
            source_id="threatfox",
            outcome=ConnectorOutcome.SUCCESS if observations else ConnectorOutcome.NO_RESULT,
            observations=observations,
            raw_reference=self.api_url,
        )

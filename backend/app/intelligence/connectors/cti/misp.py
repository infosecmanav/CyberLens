import ipaddress
import os
from typing import Any
from urllib.parse import urlsplit

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


def _safe_misp_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("MISP_URL must be an HTTPS base URL without credentials or query data")
    if parsed.hostname == "localhost" or parsed.hostname.endswith(".localhost"):
        raise ValueError("MISP_URL cannot target localhost")
    try:
        address = ipaddress.ip_address(parsed.hostname)
        if not address.is_global:
            raise ValueError("MISP_URL cannot target a private or reserved IP address")
    except ValueError as exc:
        if "MISP_URL" in str(exc):
            raise
    return value.rstrip("/")


class MispConnector(BaseIntelligenceConnector):
    manifest = ConnectorManifest(
        source_id="misp",
        name="MISP REST API",
        capabilities=[
            ConnectorCapability(
                operation="lookup",
                entity_types={
                    "IPV4", "IPV6", "DOMAIN", "URL", "MD5", "SHA1", "SHA256", "EMAIL", "CVE"
                },
                requires_authentication=True,
            )
        ],
        required_environment_variables=["MISP_URL", "MISP_API_KEY"],
        default_timeout_seconds=20.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def _post(self, url: str, api_key: str, value: str) -> httpx.Response:
        headers = {"Authorization": api_key, "Accept": "application/json"}
        body = {"returnFormat": "json", "value": value, "limit": 20, "includeEventTags": True}
        endpoint = f"{url}/attributes/restSearch"
        if self._client is not None:
            return await self._client.post(endpoint, headers=headers, json=body)
        async with httpx.AsyncClient(follow_redirects=False) as client:
            return await client.post(endpoint, headers=headers, json=body)

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if (
            request.entity is None
            or request.entity.entity_type not in self.manifest.capabilities[0].entity_types
        ):
            return self.not_supported("lookup for this entity type")
        raw_url = os.getenv("MISP_URL")
        api_key = os.getenv("MISP_API_KEY")
        if not raw_url or not api_key:
            return ConnectorResult(
                source_id="misp",
                outcome=ConnectorOutcome.NOT_CONFIGURED,
                message="MISP_URL and MISP_API_KEY must both be configured",
            )
        try:
            base_url = _safe_misp_url(raw_url)
        except ValueError as exc:
            return ConnectorResult(
                source_id="misp", outcome=ConnectorOutcome.NOT_CONFIGURED, message=str(exc)
            )
        try:
            response = await self._post(base_url, api_key, request.entity.value)
        except httpx.TimeoutException:
            return ConnectorResult(source_id="misp", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="misp", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("misp", "MISP", response)
        try:
            payload: Any = response.json()
            response_body = payload.get("response") if isinstance(payload, dict) else None
            records = response_body.get("Attribute") if isinstance(response_body, dict) else None
            if records is None and isinstance(payload, dict):
                records = payload.get("Attribute")
            if not isinstance(records, list):
                raise ValueError("MISP response is missing an Attribute list")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="misp", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        observations: list[NormalizedObservation] = []
        for record in records[:20]:
            if not isinstance(record, dict):
                continue
            event_id = record.get("event_id")
            reference = f"{base_url}/events/view/{event_id}" if event_id else base_url
            observations.append(
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="MISP_ATTRIBUTE",
                    summary=f"MISP matched attribute type {record.get('type', 'unknown')}.",
                    observed_at=parse_timestamp(record.get("timestamp")),
                    source_reference=reference,
                    attributes={
                        "attribute_type": record.get("type"),
                        "category": record.get("category"),
                        "event_id": event_id,
                        "to_ids": record.get("to_ids"),
                        "tags": record.get("Tag") or [],
                    },
                    raw_record=record,
                    external_id=str(record.get("uuid") or record.get("id") or request.entity.value),
                )
            )
        return ConnectorResult(
            source_id="misp",
            outcome=ConnectorOutcome.SUCCESS if observations else ConnectorOutcome.NO_RESULT,
            observations=observations,
            raw_reference=f"{base_url}/attributes/restSearch",
        )

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


class CensysConnector(BaseIntelligenceConnector):
    api_root = "https://api.platform.censys.io/v3/global/asset/host"
    manifest = ConnectorManifest(
        source_id="censys",
        name="Censys Platform API",
        capabilities=[
            ConnectorCapability(
                operation="lookup",
                entity_types={"IPV4", "IPV6"},
                requires_authentication=True,
            )
        ],
        required_environment_variables=["CENSYS_API_TOKEN"],
        default_timeout_seconds=15.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if request.entity is None or request.entity.entity_type not in {"IPV4", "IPV6"}:
            return self.not_supported("lookup for this entity type")
        token = os.getenv("CENSYS_API_TOKEN")
        if not token:
            return ConnectorResult(
                source_id="censys",
                outcome=ConnectorOutcome.NOT_CONFIGURED,
                message="CENSYS_API_TOKEN is not configured",
            )
        url = f"{self.api_root}/{request.entity.value}"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            if self._client is not None:
                response = await self._client.get(url, headers=headers)
            else:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(url, headers=headers)
        except httpx.TimeoutException:
            return ConnectorResult(source_id="censys", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="censys", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("censys", "Censys", response)
        try:
            payload: Any = response.json()
            result = payload.get("result") if isinstance(payload, dict) else None
            resource = result.get("resource") if isinstance(result, dict) else None
            if not isinstance(resource, dict):
                raise ValueError("Censys response is missing result.resource")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="censys", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        raw_services = resource.get("services")
        services: list[Any] = list(raw_services) if isinstance(raw_services, list) else []
        return ConnectorResult(
            source_id="censys",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=url,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="INTERNET_EXPOSURE",
                    summary=f"Censys reports {len(services)} observed service(s) for this host.",
                    observed_at=parse_timestamp(resource.get("last_updated_at")),
                    source_reference=f"https://search.censys.io/hosts/{request.entity.value}",
                    attributes={
                        "services": services[:100],
                        "dns": resource.get("dns") or {},
                        "location": resource.get("location") or {},
                        "autonomous_system": resource.get("autonomous_system") or {},
                    },
                    raw_record=resource,
                    external_id=request.entity.value,
                )
            ],
        )

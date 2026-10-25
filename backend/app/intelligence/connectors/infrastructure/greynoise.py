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


class GreyNoiseConnector(BaseIntelligenceConnector):
    api_root = "https://api.greynoise.io/v3/community"
    manifest = ConnectorManifest(
        source_id="greynoise",
        name="GreyNoise Community API",
        capabilities=[
            ConnectorCapability(
                operation="lookup", entity_types={"IPV4"}, requires_authentication=True
            )
        ],
        required_environment_variables=["GREYNOISE_API_KEY"],
        default_timeout_seconds=15.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if request.entity is None or request.entity.entity_type != "IPV4":
            return self.not_supported("lookup for this entity type")
        key = os.getenv("GREYNOISE_API_KEY")
        if not key:
            return ConnectorResult(
                source_id="greynoise",
                outcome=ConnectorOutcome.NOT_CONFIGURED,
                message="GREYNOISE_API_KEY is not configured",
            )
        url = f"{self.api_root}/{request.entity.value}"
        try:
            if self._client is not None:
                response = await self._client.get(url, headers={"key": key})
            else:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(url, headers={"key": key})
        except httpx.TimeoutException:
            return ConnectorResult(source_id="greynoise", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="greynoise", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("greynoise", "GreyNoise", response)
        try:
            record: Any = response.json()
            if not isinstance(record, dict) or not isinstance(record.get("ip"), str):
                raise ValueError("GreyNoise response is missing ip")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="greynoise", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        classification = str(record.get("classification") or "unknown")
        return ConnectorResult(
            source_id="greynoise",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=url,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="INTERNET_SCANNER_CONTEXT",
                    summary=f"GreyNoise classifies this IP as {classification} scanner context.",
                    observed_at=parse_timestamp(record.get("last_seen")),
                    source_reference=f"https://viz.greynoise.io/ip/{request.entity.value}",
                    attributes={
                        "noise": record.get("noise"),
                        "riot": record.get("riot"),
                        "classification": classification,
                        "name": record.get("name"),
                        "link": record.get("link"),
                        "message": record.get("message"),
                    },
                    raw_record=record,
                    external_id=request.entity.value,
                )
            ],
        )

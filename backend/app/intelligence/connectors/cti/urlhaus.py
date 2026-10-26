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


class UrlhausConnector(BaseIntelligenceConnector):
    api_root = "https://urlhaus-api.abuse.ch/v1"
    manifest = ConnectorManifest(
        source_id="urlhaus",
        name="URLhaus",
        capabilities=[
            ConnectorCapability(
                operation="lookup",
                entity_types={"DOMAIN", "URL", "IPV4", "IPV6"},
                requires_authentication=True,
            )
        ],
        required_environment_variables=["ABUSECH_AUTH_KEY"],
        default_timeout_seconds=15.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if request.entity is None or request.entity.entity_type not in {
            "DOMAIN",
            "URL",
            "IPV4",
            "IPV6",
        }:
            return self.not_supported("lookup for this entity type")
        key = os.getenv("ABUSECH_AUTH_KEY")
        if not key:
            return ConnectorResult(
                source_id="urlhaus",
                outcome=ConnectorOutcome.NOT_CONFIGURED,
                message="ABUSECH_AUTH_KEY is not configured",
            )
        kind = "url" if request.entity.entity_type == "URL" else "host"
        endpoint = f"{self.api_root}/{kind}/"
        form = {kind: request.entity.value}
        try:
            if self._client is not None:
                response = await self._client.post(
                    endpoint, headers={"Auth-Key": key}, data=form
                )
            else:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.post(
                        endpoint, headers={"Auth-Key": key}, data=form
                    )
        except httpx.TimeoutException:
            return ConnectorResult(source_id="urlhaus", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="urlhaus", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("urlhaus", "URLhaus", response)
        try:
            record: Any = response.json()
            status = record.get("query_status") if isinstance(record, dict) else None
            if status in {"no_results", "invalid_url", "invalid_host"}:
                return ConnectorResult(source_id="urlhaus", outcome=ConnectorOutcome.NO_RESULT)
            if status != "ok" or not isinstance(record, dict):
                raise ValueError("URLhaus response does not contain an accepted record")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="urlhaus", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        raw_urls = record.get("urls")
        raw_tags = record.get("tags")
        urls: list[Any] = list(raw_urls) if isinstance(raw_urls, list) else []
        tags: list[Any] = list(raw_tags) if isinstance(raw_tags, list) else []
        return ConnectorResult(
            source_id="urlhaus",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=endpoint,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="MALWARE_DISTRIBUTION_CONTEXT",
                    summary=(
                        f"URLhaus returned {len(urls) if urls else 1} malware URL record(s) "
                        "for this indicator."
                    ),
                    observed_at=parse_timestamp(
                        record.get("date_added") or record.get("last_online")
                    ),
                    source_reference=str(
                        record.get("urlhaus_reference") or "https://urlhaus.abuse.ch"
                    ),
                    attributes={
                        "url_status": record.get("url_status"),
                        "threat": record.get("threat"),
                        "tags": tags[:50],
                        "url_count": len(urls),
                    },
                    raw_record=record,
                    external_id=str(record.get("id") or request.entity.value),
                )
            ],
        )

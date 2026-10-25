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


class UrlscanConnector(BaseIntelligenceConnector):
    api_url = "https://urlscan.io/api/v1/search/"
    manifest = ConnectorManifest(
        source_id="urlscan",
        name="urlscan.io search API",
        capabilities=[
            ConnectorCapability(operation="lookup", entity_types={"DOMAIN", "URL", "IPV4", "IPV6"})
        ],
        required_environment_variables=[],
        default_timeout_seconds=15.0,
        active_requests_allowed=False,
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
        query_field = {
            "DOMAIN": "domain",
            "URL": "page.url",
            "IPV4": "ip",
            "IPV6": "ip",
        }[request.entity.entity_type]
        headers: dict[str, str] = {}
        key = os.getenv("URLSCAN_API_KEY")
        if key:
            headers["api-key"] = key
        params = {"q": f'{query_field}:"{request.entity.value}"', "size": "20"}
        try:
            if self._client is not None:
                response = await self._client.get(self.api_url, headers=headers, params=params)
            else:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(self.api_url, headers=headers, params=params)
        except httpx.TimeoutException:
            return ConnectorResult(source_id="urlscan", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="urlscan", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("urlscan", "urlscan.io", response)
        try:
            payload: Any = response.json()
            results = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(results, list):
                raise ValueError("urlscan.io response is missing results")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="urlscan", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        if not results:
            return ConnectorResult(source_id="urlscan", outcome=ConnectorOutcome.NO_RESULT)
        bounded = [item for item in results[:20] if isinstance(item, dict)]
        latest: dict[str, Any] = bounded[0] if bounded else {}
        raw_task = latest.get("task")
        raw_page = latest.get("page")
        raw_stats = latest.get("stats")
        task: dict[str, Any] = dict(raw_task) if isinstance(raw_task, dict) else {}
        page: dict[str, Any] = dict(raw_page) if isinstance(raw_page, dict) else {}
        stats: dict[str, Any] = dict(raw_stats) if isinstance(raw_stats, dict) else {}
        return ConnectorResult(
            source_id="urlscan",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=str(response.url),
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="URLSCAN_SEARCH_CONTEXT",
                    summary=f"urlscan.io returned {len(results)} historical search result(s).",
                    observed_at=parse_timestamp(task.get("time")),
                    source_reference=str(task.get("reportURL") or "https://urlscan.io/search/"),
                    attributes={
                        "result_count": len(results),
                        "latest_domain": page.get("domain"),
                        "latest_ip": page.get("ip"),
                        "latest_country": page.get("country"),
                        "latest_server": page.get("server"),
                        "latest_stats": stats,
                        "submission_enabled": False,
                    },
                    raw_record={"results": bounded, "truncated": len(results) > 20},
                    external_id=str(task.get("uuid") or request.entity.value),
                )
            ],
        )

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from app.intelligence.connectors.base import BaseIntelligenceConnector
from app.intelligence.connectors.http_support import http_error, parse_timestamp
from app.intelligence.connectors.models import (
    ConnectorCapability,
    ConnectorIssue,
    ConnectorManifest,
    ConnectorOutcome,
    ConnectorRequest,
    ConnectorResult,
    IntelligenceEntity,
    NormalizedObservation,
)


class FeodoTrackerConnector(BaseIntelligenceConnector):
    feed_url = "https://feodotracker.abuse.ch/downloads/ipblocklist.json"
    manifest = ConnectorManifest(
        source_id="feodo-tracker",
        name="Feodo Tracker",
        capabilities=[ConnectorCapability(operation="fetch_feed", entity_types={"IPV4"})],
        default_timeout_seconds=20.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None, cache_seconds: int = 900) -> None:
        self._client = client
        self._cache_seconds = cache_seconds
        self._cache: list[Any] | None = None
        self._cached_at = 0.0
        self._lock = asyncio.Lock()

    async def _records(self) -> tuple[list[Any] | None, ConnectorResult | None]:
        if self._cache is not None and time.monotonic() - self._cached_at < self._cache_seconds:
            return self._cache, None
        async with self._lock:
            if self._cache is not None and time.monotonic() - self._cached_at < self._cache_seconds:
                return self._cache, None
            try:
                if self._client is not None:
                    response = await self._client.get(self.feed_url)
                else:
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        response = await client.get(self.feed_url)
            except httpx.TimeoutException:
                return None, ConnectorResult(
                    source_id="feodo-tracker", outcome=ConnectorOutcome.TIMEOUT
                )
            except httpx.RequestError as exc:
                return None, ConnectorResult(
                    source_id="feodo-tracker",
                    outcome=ConnectorOutcome.NETWORK_ERROR,
                    message=str(exc),
                )
            if response.status_code != 200:
                return None, http_error("feodo-tracker", "Feodo Tracker", response)
            try:
                payload: Any = response.json()
                if not isinstance(payload, list):
                    raise ValueError("Feodo Tracker response is not a record list")
                self._cache = payload
                self._cached_at = time.monotonic()
                return payload, None
            except (ValueError, TypeError) as exc:
                return None, ConnectorResult(
                    source_id="feodo-tracker",
                    outcome=ConnectorOutcome.PARSE_ERROR,
                    message=str(exc),
                )

    async def fetch_feed(self, request: ConnectorRequest) -> ConnectorResult:
        records, error = await self._records()
        if error is not None:
            return error
        assert records is not None
        selected = records[: request.limit]
        observations: list[NormalizedObservation] = []
        issues: list[ConnectorIssue] = []
        for index, record in enumerate(selected):
            if not isinstance(record, dict) or not isinstance(record.get("ip_address"), str):
                issues.append(
                    ConnectorIssue(
                        record_index=index,
                        code="INVALID_FEODO_RECORD",
                        message="Feodo Tracker record is missing ip_address",
                        raw_record=record if isinstance(record, dict) else {},
                    )
                )
                continue
            ip_address = record["ip_address"]
            port = record.get("port")
            malware = record.get("malware") or "banking-trojan infrastructure"
            observations.append(
                NormalizedObservation(
                    entity=IntelligenceEntity(entity_type="IPV4", value=ip_address),
                    observation_type="BOTNET_COMMAND_AND_CONTROL",
                    summary=(
                        f"Feodo Tracker lists {ip_address}"
                        f"{f':{port}' if port else ''} as {malware} infrastructure."
                    ),
                    observed_at=parse_timestamp(record.get("last_online") or datetime.now(UTC)),
                    source_reference="https://feodotracker.abuse.ch/blocklist/",
                    attributes={
                        "port": port,
                        "status": record.get("status"),
                        "hostname": record.get("hostname"),
                        "asn": record.get("as_number"),
                        "country": record.get("country"),
                        "malware": malware,
                        "first_seen": record.get("first_seen"),
                        "last_online": record.get("last_online"),
                    },
                    raw_record=record,
                    external_id=f"{ip_address}:{port}" if port else ip_address,
                )
            )
        return ConnectorResult(
            source_id="feodo-tracker",
            outcome=ConnectorOutcome.SUCCESS,
            observations=observations,
            issues=issues,
            message=(
                f"Feed was bounded to {request.limit} records"
                if len(records) > request.limit
                else None
            ),
            raw_reference=self.feed_url,
        )

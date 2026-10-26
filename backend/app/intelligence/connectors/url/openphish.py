import asyncio
import hashlib
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

from app.intelligence.connectors.base import BaseIntelligenceConnector
from app.intelligence.connectors.http_support import http_error
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


class OpenPhishConnector(BaseIntelligenceConnector):
    """Read-only ingestion of the OpenPhish community URL feed."""

    feed_url = "https://openphish.com/feed.txt"
    manifest = ConnectorManifest(
        source_id="openphish",
        name="OpenPhish community feed",
        capabilities=[ConnectorCapability(operation="fetch_feed", entity_types={"URL"})],
        default_timeout_seconds=20.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None, cache_seconds: int = 1800) -> None:
        self._client = client
        self._cache_seconds = cache_seconds
        self._cache: list[str] | None = None
        self._cached_at = 0.0
        self._lock = asyncio.Lock()

    async def _records(self) -> tuple[list[str] | None, ConnectorResult | None]:
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
                    source_id=self.manifest.source_id,
                    outcome=ConnectorOutcome.TIMEOUT,
                )
            except httpx.RequestError as exc:
                return None, ConnectorResult(
                    source_id=self.manifest.source_id,
                    outcome=ConnectorOutcome.NETWORK_ERROR,
                    message=str(exc),
                )
            if response.status_code != 200:
                return None, http_error(self.manifest.source_id, self.manifest.name, response)
            records = [line.strip() for line in response.text.splitlines() if line.strip()]
            self._cache = records
            self._cached_at = time.monotonic()
            return records, None

    async def fetch_feed(self, request: ConnectorRequest) -> ConnectorResult:
        records, error = await self._records()
        if error is not None:
            return error
        assert records is not None
        observations: list[NormalizedObservation] = []
        issues: list[ConnectorIssue] = []
        for index, value in enumerate(records[: request.limit]):
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
            ):
                issues.append(
                    ConnectorIssue(
                        record_index=index,
                        code="INVALID_OPENPHISH_RECORD",
                        message="OpenPhish record is not a supported HTTP(S) URL",
                        raw_record={"url": value},
                    )
                )
                continue
            digest = hashlib.sha256(value.encode()).hexdigest()
            observations.append(
                NormalizedObservation(
                    entity=IntelligenceEntity(entity_type="URL", value=value),
                    observation_type="PHISHING_URL_FEED_ENTRY",
                    summary="OpenPhish lists this URL in its community phishing feed.",
                    observed_at=datetime.now(UTC),
                    source_reference="https://openphish.com/",
                    attributes={
                        "feed": "community",
                        "classification": "phishing",
                        "analyst_validation_required": True,
                    },
                    raw_record={"url": value},
                    external_id=digest,
                )
            )
        return ConnectorResult(
            source_id=self.manifest.source_id,
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

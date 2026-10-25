import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from app.intelligence.connectors.base import BaseIntelligenceConnector
from app.intelligence.connectors.http_support import http_error
from app.intelligence.connectors.models import (
    ConnectorCapability,
    ConnectorManifest,
    ConnectorOutcome,
    ConnectorRequest,
    ConnectorResult,
    NormalizedObservation,
)


class MitreAttackConnector(BaseIntelligenceConnector):
    bundle_url = (
        "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
        "enterprise-attack/enterprise-attack.json"
    )
    manifest = ConnectorManifest(
        source_id="attack-enterprise",
        name="MITRE ATT&CK Enterprise",
        capabilities=[
            ConnectorCapability(operation="lookup", entity_types={"ATTACK_TECHNIQUE"})
        ],
        default_timeout_seconds=20.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None, cache_seconds: int = 3600) -> None:
        self._client = client
        self._cache_seconds = cache_seconds
        self._cache: dict[str, dict[str, Any]] | None = None
        self._cached_at = 0.0
        self._lock = asyncio.Lock()

    async def _get(self) -> httpx.Response:
        if self._client is not None:
            return await self._client.get(self.bundle_url)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            return await client.get(self.bundle_url)

    async def _techniques(self) -> tuple[dict[str, dict[str, Any]] | None, ConnectorResult | None]:
        if self._cache is not None and time.monotonic() - self._cached_at < self._cache_seconds:
            return self._cache, None
        async with self._lock:
            if self._cache is not None and time.monotonic() - self._cached_at < self._cache_seconds:
                return self._cache, None
            try:
                response = await self._get()
            except httpx.TimeoutException:
                return None, ConnectorResult(
                    source_id="attack-enterprise", outcome=ConnectorOutcome.TIMEOUT
                )
            except httpx.RequestError as exc:
                return None, ConnectorResult(
                    source_id="attack-enterprise",
                    outcome=ConnectorOutcome.NETWORK_ERROR,
                    message=str(exc),
                )
            if response.status_code != 200:
                return None, http_error("attack-enterprise", "MITRE ATT&CK", response)
            try:
                payload: Any = response.json()
                objects = payload.get("objects") if isinstance(payload, dict) else None
                if not isinstance(objects, list):
                    raise ValueError("ATT&CK bundle is missing objects")
                techniques: dict[str, dict[str, Any]] = {}
                for item in objects:
                    if not isinstance(item, dict) or item.get("type") != "attack-pattern":
                        continue
                    references = item.get("external_references")
                    for reference in references if isinstance(references, list) else []:
                        if (
                            isinstance(reference, dict)
                            and reference.get("source_name") == "mitre-attack"
                            and isinstance(reference.get("external_id"), str)
                        ):
                            techniques[reference["external_id"].upper()] = item
                self._cache = techniques
                self._cached_at = time.monotonic()
                return techniques, None
            except (ValueError, TypeError) as exc:
                return None, ConnectorResult(
                    source_id="attack-enterprise",
                    outcome=ConnectorOutcome.PARSE_ERROR,
                    message=str(exc),
                )

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if request.entity is None or request.entity.entity_type != "ATTACK_TECHNIQUE":
            return self.not_supported("lookup for this entity type")
        techniques, error = await self._techniques()
        if error is not None:
            return error
        assert techniques is not None
        technique_id = request.entity.value.upper()
        record = techniques.get(technique_id)
        if record is None:
            return ConnectorResult(
                source_id="attack-enterprise", outcome=ConnectorOutcome.NO_RESULT
            )
        modified = record.get("modified")
        observed_at = datetime.now(UTC)
        if isinstance(modified, str):
            try:
                observed_at = datetime.fromisoformat(modified.replace("Z", "+00:00"))
            except ValueError:
                pass
        return ConnectorResult(
            source_id="attack-enterprise",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=self.bundle_url,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="ATTACK_TECHNIQUE",
                    summary=str(record.get("description") or record.get("name") or technique_id),
                    observed_at=observed_at,
                    source_reference=(
                        "https://attack.mitre.org/techniques/"
                        f"{technique_id.replace('.', '/')}/"
                    ),
                    attributes={
                        "name": record.get("name"),
                        "kill_chain_phases": record.get("kill_chain_phases") or [],
                        "revoked": bool(record.get("revoked", False)),
                        "deprecated": bool(record.get("x_mitre_deprecated", False)),
                        "platforms": record.get("x_mitre_platforms") or [],
                    },
                    raw_record=record,
                    external_id=technique_id,
                )
            ],
        )

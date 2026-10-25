from datetime import UTC, datetime
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


class CrtShConnector(BaseIntelligenceConnector):
    api_url = "https://crt.sh/"
    manifest = ConnectorManifest(
        source_id="crt-sh",
        name="crt.sh certificate transparency",
        capabilities=[ConnectorCapability(operation="lookup", entity_types={"DOMAIN"})],
        default_timeout_seconds=20.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if request.entity is None or request.entity.entity_type != "DOMAIN":
            return self.not_supported("lookup for this entity type")
        params = {"q": request.entity.value, "output": "json"}
        try:
            if self._client is not None:
                response = await self._client.get(self.api_url, params=params)
            else:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(self.api_url, params=params)
        except httpx.TimeoutException:
            return ConnectorResult(source_id="crt-sh", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="crt-sh", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("crt-sh", "crt.sh", response)
        try:
            payload: Any = response.json()
            if not isinstance(payload, list):
                raise ValueError("crt.sh response is not a certificate list")
            records = [record for record in payload if isinstance(record, dict)]
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="crt-sh", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        if not records:
            return ConnectorResult(source_id="crt-sh", outcome=ConnectorOutcome.NO_RESULT)
        bounded = records[:100]
        observed_at = max(
            (parse_timestamp(record.get("not_before")) for record in bounded),
            default=datetime.now(UTC),
        )
        names = sorted(
            {
                name.strip().lower()
                for record in bounded
                for name in str(record.get("name_value") or "").splitlines()
                if name.strip()
            }
        )[:200]
        return ConnectorResult(
            source_id="crt-sh",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=str(response.url),
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="CERTIFICATE_TRANSPARENCY",
                    summary=f"crt.sh returned {len(records)} certificate record(s).",
                    observed_at=observed_at,
                    source_reference=f"https://crt.sh/?q={request.entity.value}",
                    attributes={
                        "certificate_count": len(records),
                        "bounded_records": len(bounded),
                        "dns_names": names,
                    },
                    raw_record={"certificates": bounded, "truncated": len(records) > 100},
                    external_id=request.entity.value,
                )
            ],
        )

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


class AbuseIpDbConnector(BaseIntelligenceConnector):
    api_url = "https://api.abuseipdb.com/api/v2/check"
    manifest = ConnectorManifest(
        source_id="abuseipdb",
        name="AbuseIPDB API v2",
        capabilities=[
            ConnectorCapability(
                operation="lookup",
                entity_types={"IPV4", "IPV6"},
                requires_authentication=True,
            )
        ],
        required_environment_variables=["ABUSEIPDB_API_KEY"],
        default_timeout_seconds=15.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if request.entity is None or request.entity.entity_type not in {"IPV4", "IPV6"}:
            return self.not_supported("lookup for this entity type")
        key = os.getenv("ABUSEIPDB_API_KEY")
        if not key:
            return ConnectorResult(
                source_id="abuseipdb",
                outcome=ConnectorOutcome.NOT_CONFIGURED,
                message="ABUSEIPDB_API_KEY is not configured",
            )
        headers = {"Key": key, "Accept": "application/json"}
        params = {"ipAddress": request.entity.value, "maxAgeInDays": "90"}
        try:
            if self._client is not None:
                response = await self._client.get(self.api_url, headers=headers, params=params)
            else:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(self.api_url, headers=headers, params=params)
        except httpx.TimeoutException:
            return ConnectorResult(source_id="abuseipdb", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="abuseipdb", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("abuseipdb", "AbuseIPDB", response)
        try:
            payload: Any = response.json()
            record = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(record, dict) or not isinstance(record.get("ipAddress"), str):
                raise ValueError("AbuseIPDB response is missing data.ipAddress")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="abuseipdb", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        score = record.get("abuseConfidenceScore")
        reports = record.get("totalReports")
        return ConnectorResult(
            source_id="abuseipdb",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=self.api_url,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="COMMUNITY_ABUSE_REPORTS",
                    summary=(
                        f"AbuseIPDB reports score {score} with {reports} report(s); "
                        "this reputation signal requires analyst context."
                    ),
                    observed_at=parse_timestamp(record.get("lastReportedAt")),
                    source_reference=f"https://www.abuseipdb.com/check/{request.entity.value}",
                    attributes={
                        "abuse_confidence_score": score,
                        "total_reports": reports,
                        "distinct_users": record.get("numDistinctUsers"),
                        "usage_type": record.get("usageType"),
                        "isp": record.get("isp"),
                        "domain": record.get("domain"),
                        "country_code": record.get("countryCode"),
                        "is_tor": record.get("isTor"),
                    },
                    raw_record=record,
                    external_id=request.entity.value,
                )
            ],
        )

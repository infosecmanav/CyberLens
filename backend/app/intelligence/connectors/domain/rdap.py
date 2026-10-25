from typing import Any
from urllib.parse import quote

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


class RdapConnector(BaseIntelligenceConnector):
    api_root = "https://rdap.org"
    manifest = ConnectorManifest(
        source_id="rdap",
        name="RDAP bootstrap service",
        capabilities=[
            ConnectorCapability(operation="lookup", entity_types={"IPV4", "IPV6", "DOMAIN"})
        ],
        default_timeout_seconds=15.0,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if request.entity is None or request.entity.entity_type not in {"IPV4", "IPV6", "DOMAIN"}:
            return self.not_supported("lookup for this entity type")
        kind = "domain" if request.entity.entity_type == "DOMAIN" else "ip"
        url = f"{self.api_root}/{kind}/{quote(request.entity.value, safe=':.')}"
        try:
            if self._client is not None:
                response = await self._client.get(url)
            else:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(url)
        except httpx.TimeoutException:
            return ConnectorResult(source_id="rdap", outcome=ConnectorOutcome.TIMEOUT)
        except httpx.RequestError as exc:
            return ConnectorResult(
                source_id="rdap", outcome=ConnectorOutcome.NETWORK_ERROR, message=str(exc)
            )
        if response.status_code != 200:
            return http_error("rdap", "RDAP", response)
        try:
            record: Any = response.json()
            if not isinstance(record, dict) or not (
                isinstance(record.get("handle"), str)
                or isinstance(record.get("ldhName"), str)
                or isinstance(record.get("name"), str)
            ):
                raise ValueError("RDAP response is missing an object identifier")
        except (ValueError, TypeError) as exc:
            return ConnectorResult(
                source_id="rdap", outcome=ConnectorOutcome.PARSE_ERROR, message=str(exc)
            )
        raw_events = record.get("events")
        events: list[Any] = list(raw_events) if isinstance(raw_events, list) else []
        latest_event = next(
            (event for event in reversed(events) if isinstance(event, dict)), {}
        )
        nameservers = record.get("nameservers")
        nameserver_names = [
            item.get("ldhName")
            for item in (nameservers if isinstance(nameservers, list) else [])[:50]
            if isinstance(item, dict) and item.get("ldhName")
        ]
        return ConnectorResult(
            source_id="rdap",
            outcome=ConnectorOutcome.SUCCESS,
            raw_reference=url,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="REGISTRATION_CONTEXT",
                    summary=(
                        f"RDAP returned registration object "
                        f"{record.get('handle') or record.get('ldhName') or record.get('name')}."
                    ),
                    observed_at=parse_timestamp(latest_event.get("eventDate")),
                    source_reference=url,
                    attributes={
                        "handle": record.get("handle"),
                        "name": record.get("ldhName") or record.get("name"),
                        "status": record.get("status") or [],
                        "start_address": record.get("startAddress"),
                        "end_address": record.get("endAddress"),
                        "nameservers": nameserver_names,
                        "events": events[:50],
                    },
                    raw_record=record,
                    external_id=str(
                        record.get("handle")
                        or record.get("ldhName")
                        or record.get("name")
                    ),
                )
            ],
        )

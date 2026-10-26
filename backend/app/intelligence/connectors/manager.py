import asyncio

from app.intelligence.connectors.base import BaseIntelligenceConnector
from app.intelligence.connectors.models import (
    ConnectorOutcome,
    ConnectorRequest,
    ConnectorResult,
)
from app.intelligence.connectors.registry import ConnectorRegistry


class ConnectorManager:
    def __init__(self, registry: ConnectorRegistry, max_concurrency: int = 5) -> None:
        self.registry = registry
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def lookup(
        self,
        request: ConnectorRequest,
        source_ids: set[str] | None = None,
    ) -> list[ConnectorResult]:
        if request.entity is None:
            raise ValueError("A lookup request requires an entity")
        connectors = self.registry.applicable("lookup", request.entity.entity_type)
        if source_ids is not None:
            connectors = [c for c in connectors if c.manifest.source_id in source_ids]
        return await asyncio.gather(
            *(self._safe_lookup(connector, request) for connector in connectors)
        )

    async def fetch_feed(
        self,
        request: ConnectorRequest,
        source_ids: set[str] | None = None,
    ) -> list[ConnectorResult]:
        connectors = [
            connector
            for connector in self.registry.all()
            if any(
                capability.operation == "fetch_feed"
                for capability in connector.manifest.capabilities
            )
        ]
        if source_ids is not None:
            connectors = [c for c in connectors if c.manifest.source_id in source_ids]
        return await asyncio.gather(
            *(self._safe_fetch_feed(connector, request) for connector in connectors)
        )

    async def _safe_lookup(
        self,
        connector: BaseIntelligenceConnector,
        request: ConnectorRequest,
    ) -> ConnectorResult:
        source_id = connector.manifest.source_id
        timeout = connector.manifest.default_timeout_seconds
        try:
            async with self._semaphore:
                async with asyncio.timeout(timeout):
                    return await connector.lookup(request)
        except TimeoutError:
            return ConnectorResult(source_id=source_id, outcome=ConnectorOutcome.TIMEOUT)
        except OSError as exc:
            return ConnectorResult(
                source_id=source_id,
                outcome=ConnectorOutcome.NETWORK_ERROR,
                message=str(exc),
            )
        except Exception:
            return ConnectorResult(
                source_id=source_id,
                outcome=ConnectorOutcome.SOURCE_ERROR,
                message="Connector execution failed",
            )

    async def _safe_fetch_feed(
        self,
        connector: BaseIntelligenceConnector,
        request: ConnectorRequest,
    ) -> ConnectorResult:
        source_id = connector.manifest.source_id
        timeout = connector.manifest.default_timeout_seconds
        try:
            async with self._semaphore:
                async with asyncio.timeout(timeout):
                    return await connector.fetch_feed(request)
        except TimeoutError:
            return ConnectorResult(source_id=source_id, outcome=ConnectorOutcome.TIMEOUT)
        except OSError as exc:
            return ConnectorResult(
                source_id=source_id,
                outcome=ConnectorOutcome.NETWORK_ERROR,
                message=str(exc),
            )
        except Exception:
            return ConnectorResult(
                source_id=source_id,
                outcome=ConnectorOutcome.SOURCE_ERROR,
                message="Connector execution failed",
            )

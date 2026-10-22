from abc import ABC, abstractmethod

from app.intelligence.connectors.models import (
    ConnectorManifest,
    ConnectorOutcome,
    ConnectorRequest,
    ConnectorResult,
)


class BaseIntelligenceConnector(ABC):
    """Contract for capability-aware, truthful intelligence integrations."""

    @property
    @abstractmethod
    def manifest(self) -> ConnectorManifest:
        raise NotImplementedError

    async def health_check(self) -> ConnectorResult:
        return ConnectorResult(
            source_id=self.manifest.source_id,
            outcome=ConnectorOutcome.NOT_SUPPORTED,
            message="Health checks are not implemented for this connector",
        )

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        return self.not_supported("lookup")

    async def search(self, request: ConnectorRequest) -> ConnectorResult:
        return self.not_supported("search")

    async def fetch_feed(self, request: ConnectorRequest) -> ConnectorResult:
        return self.not_supported("fetch_feed")

    async def get_relationships(self, request: ConnectorRequest) -> ConnectorResult:
        return self.not_supported("get_relationships")

    async def get_report(self, request: ConnectorRequest) -> ConnectorResult:
        return self.not_supported("get_report")

    def not_supported(self, operation: str) -> ConnectorResult:
        return ConnectorResult(
            source_id=self.manifest.source_id,
            outcome=ConnectorOutcome.NOT_SUPPORTED,
            message=f"{operation} is not supported by this connector",
        )

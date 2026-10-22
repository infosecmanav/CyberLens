from app.intelligence.connectors.base import BaseIntelligenceConnector


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, BaseIntelligenceConnector] = {}

    def register(self, connector: BaseIntelligenceConnector) -> None:
        source_id = connector.manifest.source_id
        if source_id in self._connectors:
            raise ValueError(f"Connector already registered: {source_id}")
        self._connectors[source_id] = connector

    def get(self, source_id: str) -> BaseIntelligenceConnector | None:
        return self._connectors.get(source_id)

    def all(self) -> list[BaseIntelligenceConnector]:
        return list(self._connectors.values())

    def applicable(self, operation: str, entity_type: str) -> list[BaseIntelligenceConnector]:
        matches: list[BaseIntelligenceConnector] = []
        for connector in self._connectors.values():
            for capability in connector.manifest.capabilities:
                if capability.operation == operation and entity_type in capability.entity_types:
                    matches.append(connector)
                    break
        return matches

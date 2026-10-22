import asyncio

from app.intelligence.connectors.local_fixture import LocalFixtureConnector
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.connectors.models import ConnectorRequest, IntelligenceEntity
from app.intelligence.connectors.registry import ConnectorRegistry


async def test_registry_routes_supported_entities() -> None:
    registry = ConnectorRegistry()
    registry.register(LocalFixtureConnector())
    assert len(registry.applicable("lookup", "DOMAIN")) == 1
    assert registry.applicable("lookup", "EMAIL") == []


async def test_manager_returns_labelled_local_fixture() -> None:
    registry = ConnectorRegistry()
    registry.register(LocalFixtureConnector())
    manager = ConnectorManager(registry)

    results = await manager.lookup(
        ConnectorRequest(entity=IntelligenceEntity(entity_type="DOMAIN", value="example.test"))
    )
    assert results[0].outcome == "SUCCESS"
    assert results[0].observations[0].attributes["demonstration"] is True


async def test_manager_converts_timeout_to_outcome() -> None:
    class SlowConnector(LocalFixtureConnector):
        manifest = LocalFixtureConnector.manifest.model_copy(
            update={"default_timeout_seconds": 0.001}
        )

        async def lookup(self, request: ConnectorRequest):  # type: ignore[no-untyped-def]
            await asyncio.sleep(0.02)
            return await super().lookup(request)

    registry = ConnectorRegistry()
    registry.register(SlowConnector())
    results = await ConnectorManager(registry).lookup(
        ConnectorRequest(entity=IntelligenceEntity(entity_type="DOMAIN", value="example.test"))
    )
    assert results[0].outcome == "TIMEOUT"

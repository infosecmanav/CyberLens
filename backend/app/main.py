import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models as _models  # noqa: F401
from app.api.routes import (
    auth,
    cases,
    detections,
    enrichment,
    export,
    feeds,
    graph,
    health,
    intelligence,
    investigations,
    meta,
    monitoring,
    operations,
    playbooks,
    sources,
    taxii,
)
from app.core.config import Settings, get_settings
from app.db.session import (
    close_database,
    configure_database,
    create_schema,
    get_session_factory,
)
from app.intelligence.connectors.local_fixture import LocalFixtureConnector
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.connectors.registry import ConnectorRegistry
from app.intelligence.connectors.vulnerability import CisaKevConnector, NvdConnector, OsvConnector
from app.intelligence.enrichment import run_due_enrichment_policies
from app.intelligence.feeds import run_due_feed_subscriptions
from app.intelligence.seed import seed_source_catalog
from app.intelligence.taxii import TaxiiClient, run_due_collections
from app.operations.monitoring import run_due_objectives
from app.operations.seed import seed_playbooks

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_database(active_settings.database_url)
        if active_settings.auto_create_schema:
            await create_schema()
        if active_settings.seed_source_catalog:
            async with get_session_factory()() as session:
                await seed_source_catalog(session)
        if active_settings.seed_default_playbooks:
            async with get_session_factory()() as session:
                await seed_playbooks(session)
        http_client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(10.0),
            headers={"User-Agent": f"ThreatLens/{active_settings.app_version}"},
        )
        registry = ConnectorRegistry()
        registry.register(LocalFixtureConnector())
        registry.register(CisaKevConnector(http_client))
        registry.register(NvdConnector(http_client))
        registry.register(OsvConnector(http_client))
        manager = ConnectorManager(registry)
        application.state.connector_manager = manager
        taxii_client = TaxiiClient(http_client)
        application.state.taxii_client = taxii_client

        async def monitor_due() -> None:
            while True:
                await asyncio.sleep(active_settings.monitoring_poll_seconds)
                try:
                    async with get_session_factory()() as session:
                        await run_due_objectives(session, manager)
                    async with get_session_factory()() as session:
                        await run_due_collections(session, taxii_client)
                    async with get_session_factory()() as session:
                        await run_due_enrichment_policies(session, manager)
                    async with get_session_factory()() as session:
                        await run_due_feed_subscriptions(session, manager)
                except Exception:
                    logger.exception("Scheduled monitoring cycle failed")

        scheduler: asyncio.Task[None] | None = None
        if active_settings.monitoring_scheduler_enabled and active_settings.app_env != "test":
            scheduler = asyncio.create_task(monitor_due())
        yield
        if scheduler is not None:
            scheduler.cancel()
            with suppress(asyncio.CancelledError):
                await scheduler
        await http_client.aclose()
        await close_database()

    application = FastAPI(
        title=active_settings.app_name,
        version=active_settings.app_version,
        description="Evidence-backed cyber-threat intelligence and investigation platform",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    application.state.settings = active_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router, prefix=active_settings.api_v1_prefix)
    application.include_router(meta.router, prefix=active_settings.api_v1_prefix)
    application.include_router(auth.router, prefix=active_settings.api_v1_prefix)
    application.include_router(sources.router, prefix=active_settings.api_v1_prefix)
    application.include_router(intelligence.router, prefix=active_settings.api_v1_prefix)
    application.include_router(investigations.router, prefix=active_settings.api_v1_prefix)
    application.include_router(graph.router, prefix=active_settings.api_v1_prefix)
    application.include_router(detections.router, prefix=active_settings.api_v1_prefix)
    application.include_router(cases.router, prefix=active_settings.api_v1_prefix)
    application.include_router(playbooks.router, prefix=active_settings.api_v1_prefix)
    application.include_router(monitoring.router, prefix=active_settings.api_v1_prefix)
    application.include_router(operations.router, prefix=active_settings.api_v1_prefix)
    application.include_router(taxii.router, prefix=active_settings.api_v1_prefix)
    application.include_router(enrichment.router, prefix=active_settings.api_v1_prefix)
    application.include_router(export.router, prefix=active_settings.api_v1_prefix)
    application.include_router(feeds.router, prefix=active_settings.api_v1_prefix)
    return application


app = create_app()

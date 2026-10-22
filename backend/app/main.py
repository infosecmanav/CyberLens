from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models as _models  # noqa: F401
from app.api.routes import auth, health, intelligence, meta, sources
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
from app.intelligence.connectors.vulnerability import CisaKevConnector, OsvConnector
from app.intelligence.seed import seed_source_catalog


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
        http_client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(10.0),
            headers={"User-Agent": f"ThreatLens/{active_settings.app_version}"},
        )
        registry = ConnectorRegistry()
        registry.register(LocalFixtureConnector())
        registry.register(CisaKevConnector(http_client))
        registry.register(OsvConnector(http_client))
        application.state.connector_manager = ConnectorManager(registry)
        yield
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
    return application


app = create_app()

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.dependencies import AdminUser, DatabaseSession
from app.intelligence.taxii import TaxiiClient, TaxiiError, discover_server, run_collection
from app.models import TaxiiCollection, TaxiiCollectionRun, TaxiiServer
from app.operations.audit import emit_audit
from app.schemas.taxii import (
    TaxiiCollectionResponse,
    TaxiiCollectionRunResponse,
    TaxiiCollectionUpdate,
    TaxiiServerCreate,
    TaxiiServerResponse,
)

router = APIRouter(prefix="/taxii", tags=["TAXII 2.1"])


async def _server(session: DatabaseSession, server_id: UUID) -> TaxiiServer:
    server = await session.get(TaxiiServer, server_id)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TAXII server not found")
    return server


async def _collection(session: DatabaseSession, collection_id: UUID) -> TaxiiCollection:
    collection = await session.get(TaxiiCollection, collection_id)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="TAXII collection not found"
        )
    return collection


@router.get("/servers", response_model=list[TaxiiServerResponse])
async def list_servers(session: DatabaseSession, user: AdminUser) -> list[TaxiiServerResponse]:
    del user
    servers = list((await session.scalars(select(TaxiiServer).order_by(TaxiiServer.name))).all())
    return [TaxiiServerResponse.model_validate(server) for server in servers]


@router.post(
    "/servers", response_model=TaxiiServerResponse, status_code=status.HTTP_201_CREATED
)
async def create_server(
    payload: TaxiiServerCreate, session: DatabaseSession, user: AdminUser
) -> TaxiiServerResponse:
    duplicate = await session.scalar(
        select(TaxiiServer.id).where(
            (TaxiiServer.name == payload.name)
            | (TaxiiServer.discovery_url == payload.discovery_url)
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A TAXII server already uses this name or discovery URL",
        )
    server = TaxiiServer(
        name=payload.name,
        discovery_url=payload.discovery_url,
        auth_environment_variable=payload.auth_environment_variable,
        timeout_seconds=payload.timeout_seconds,
        page_size=payload.page_size,
        max_pages=payload.max_pages,
        created_by=user.id,
    )
    session.add(server)
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="taxii.server_created",
        object_type="taxii_server",
        object_id=server.id,
        details={
            "discovery_url": server.discovery_url,
            "credential_environment": server.auth_environment_variable,
        },
    )
    await session.commit()
    await session.refresh(server)
    return TaxiiServerResponse.model_validate(server)


@router.post("/servers/{server_id}/discover", response_model=TaxiiServerResponse)
async def discover(
    server_id: UUID,
    request: Request,
    session: DatabaseSession,
    user: AdminUser,
) -> TaxiiServerResponse:
    server = await _server(session, server_id)
    client: TaxiiClient = request.app.state.taxii_client
    try:
        server = await discover_server(session, client, server, user.id)
    except TaxiiError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return TaxiiServerResponse.model_validate(server)


@router.put("/collections/{collection_id}", response_model=TaxiiCollectionResponse)
async def update_collection(
    collection_id: UUID,
    payload: TaxiiCollectionUpdate,
    session: DatabaseSession,
    user: AdminUser,
) -> TaxiiCollection:
    collection = await _collection(session, collection_id)
    if payload.selected and not collection.can_read:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The TAXII server does not authorize reads from this collection",
        )
    collection.selected = payload.selected
    collection.poll_interval_minutes = payload.poll_interval_minutes
    collection.next_run_at = datetime.now(UTC) if payload.selected else None
    emit_audit(
        session,
        actor_id=user.id,
        action="taxii.collection_configuration_updated",
        object_type="taxii_collection",
        object_id=collection.id,
        details={
            "selected": collection.selected,
            "poll_interval_minutes": collection.poll_interval_minutes,
        },
    )
    await session.commit()
    await session.refresh(collection)
    return collection


@router.post("/collections/{collection_id}/run", response_model=TaxiiCollectionRunResponse)
async def run(
    collection_id: UUID,
    request: Request,
    session: DatabaseSession,
    user: AdminUser,
) -> TaxiiCollectionRun:
    collection = await _collection(session, collection_id)
    client: TaxiiClient = request.app.state.taxii_client
    return await run_collection(session, client, collection, user.id)


@router.get("/runs", response_model=list[TaxiiCollectionRunResponse])
async def list_runs(
    session: DatabaseSession, user: AdminUser, limit: int = 50
) -> list[TaxiiCollectionRun]:
    del user
    bounded_limit = min(max(limit, 1), 200)
    return list(
        (
            await session.scalars(
                select(TaxiiCollectionRun)
                .order_by(TaxiiCollectionRun.started_at.desc())
                .limit(bounded_limit)
            )
        ).all()
    )

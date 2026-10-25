from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.dependencies import AdminUser, DatabaseSession
from app.intelligence.connectors.manager import ConnectorManager
from app.intelligence.feeds import run_feed_subscription
from app.models import FeedRun, FeedSubscription, Source
from app.operations.audit import emit_audit
from app.schemas.feeds import (
    FeedRunResponse,
    FeedSubscriptionCreate,
    FeedSubscriptionResponse,
    FeedSubscriptionUpdate,
)

router = APIRouter(prefix="/feeds", tags=["intelligence feeds"])


async def _subscription(session: DatabaseSession, subscription_id: UUID) -> FeedSubscription:
    subscription = await session.get(FeedSubscription, subscription_id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feed subscription not found"
        )
    return subscription


@router.get("/subscriptions", response_model=list[FeedSubscriptionResponse])
async def list_subscriptions(
    session: DatabaseSession, user: AdminUser
) -> list[FeedSubscriptionResponse]:
    del user
    subscriptions = list(
        (await session.scalars(select(FeedSubscription).order_by(FeedSubscription.name))).all()
    )
    return [FeedSubscriptionResponse.model_validate(item) for item in subscriptions]


@router.post(
    "/subscriptions",
    response_model=FeedSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    payload: FeedSubscriptionCreate,
    request: Request,
    session: DatabaseSession,
    user: AdminUser,
) -> FeedSubscriptionResponse:
    source = await session.scalar(select(Source).where(Source.source_id == payload.source_id))
    if source is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown source")
    manager: ConnectorManager = request.app.state.connector_manager
    connector = manager.registry.get(payload.source_id)
    supports_feed = connector is not None and any(
        capability.operation == "fetch_feed" for capability in connector.manifest.capabilities
    )
    if not supports_feed or payload.source_id == "local-fixtures":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source does not expose an automated production feed",
        )
    duplicate = await session.scalar(
        select(FeedSubscription.id).where(
            (FeedSubscription.name == payload.name) | (FeedSubscription.source_id == source.id)
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subscription already uses this name or source",
        )
    subscription = FeedSubscription(
        source_id=source.id,
        name=payload.name,
        cadence_minutes=payload.cadence_minutes,
        max_records=payload.max_records,
        enabled=True,
        created_by=user.id,
        next_run_at=datetime.now(UTC),
    )
    session.add(subscription)
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="feed.subscription_created",
        object_type="feed_subscription",
        object_id=subscription.id,
        details={
            "source_id": payload.source_id,
            "cadence_minutes": payload.cadence_minutes,
            "max_records": payload.max_records,
        },
    )
    await session.commit()
    await session.refresh(subscription)
    return FeedSubscriptionResponse.model_validate(subscription)


@router.put("/subscriptions/{subscription_id}", response_model=FeedSubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    payload: FeedSubscriptionUpdate,
    session: DatabaseSession,
    user: AdminUser,
) -> FeedSubscriptionResponse:
    subscription = await _subscription(session, subscription_id)
    subscription.enabled = payload.enabled
    subscription.cadence_minutes = payload.cadence_minutes
    subscription.max_records = payload.max_records
    subscription.next_run_at = datetime.now(UTC) if payload.enabled else None
    emit_audit(
        session,
        actor_id=user.id,
        action="feed.subscription_configuration_updated",
        object_type="feed_subscription",
        object_id=subscription.id,
        details={
            "enabled": subscription.enabled,
            "cadence_minutes": subscription.cadence_minutes,
            "max_records": subscription.max_records,
        },
    )
    await session.commit()
    await session.refresh(subscription)
    return FeedSubscriptionResponse.model_validate(subscription)


@router.post("/subscriptions/{subscription_id}/run", response_model=FeedRunResponse)
async def run_subscription(
    subscription_id: UUID,
    request: Request,
    session: DatabaseSession,
    user: AdminUser,
) -> FeedRunResponse:
    subscription = await _subscription(session, subscription_id)
    if not subscription.enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Feed is paused")
    manager: ConnectorManager = request.app.state.connector_manager
    run = await run_feed_subscription(session, manager, subscription, user.id)
    return FeedRunResponse.model_validate(run)


@router.get("/runs", response_model=list[FeedRunResponse])
async def list_runs(
    session: DatabaseSession, user: AdminUser, limit: int = 50
) -> list[FeedRunResponse]:
    del user
    runs = list(
        (
            await session.scalars(
                select(FeedRun)
                .order_by(FeedRun.started_at.desc())
                .limit(min(max(limit, 1), 200))
            )
        ).all()
    )
    return [FeedRunResponse.model_validate(run) for run in runs]

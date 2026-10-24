from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent


def emit_audit(
    session: AsyncSession,
    *,
    actor_id: UUID | None,
    action: str,
    object_type: str,
    object_id: UUID | str | None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        occurred_at=datetime.now(UTC),
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else None,
        details=details or {},
    )
    session.add(event)
    return event

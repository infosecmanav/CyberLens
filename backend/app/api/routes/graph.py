from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import AnalystUser, DatabaseSession
from app.models import Entity, EntityRelationship, Evidence
from app.operations import emit_audit
from app.schemas.operations import GraphEdge, RelationshipCreate

router = APIRouter(prefix="/graph", tags=["threat graph"])


@router.post("/relationships", response_model=GraphEdge, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    payload: RelationshipCreate,
    session: DatabaseSession,
    user: AnalystUser,
) -> GraphEdge:
    if await session.get(Entity, payload.source_entity_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source entity not found")
    if await session.get(Entity, payload.target_entity_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target entity not found")
    if payload.evidence_id is not None and await session.get(Evidence, payload.evidence_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    existing = await session.scalar(
        select(EntityRelationship).where(
            EntityRelationship.source_entity_id == payload.source_entity_id,
            EntityRelationship.target_entity_id == payload.target_entity_id,
            EntityRelationship.relationship_type == payload.relationship_type.upper(),
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Relationship already exists"
        )
    relationship = EntityRelationship(
        source_entity_id=payload.source_entity_id,
        target_entity_id=payload.target_entity_id,
        relationship_type=payload.relationship_type.upper(),
        evidence_id=payload.evidence_id,
        confidence=payload.confidence,
        provenance=payload.provenance,
        uncertainty_notes=payload.uncertainty_notes,
        first_seen=payload.first_seen,
        last_seen=payload.last_seen,
    )
    session.add(relationship)
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="RELATIONSHIP_CREATED",
        object_type="EntityRelationship",
        object_id=relationship.id,
        details={"relationship_type": relationship.relationship_type},
    )
    await session.commit()
    return GraphEdge(
        id=relationship.id,
        source=relationship.source_entity_id,
        target=relationship.target_entity_id,
        relationship_type=relationship.relationship_type,
        evidence_id=relationship.evidence_id,
        confidence=relationship.confidence,
        provenance=relationship.provenance,
        uncertainty_notes=relationship.uncertainty_notes,
        first_seen=relationship.first_seen,
        last_seen=relationship.last_seen,
    )

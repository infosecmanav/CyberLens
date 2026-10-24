from collections import deque
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    EntityRelationship,
    Investigation,
    InvestigationEntity,
    SimilarityScore,
)
from app.schemas.operations import GraphEdge, GraphNode


async def build_investigation_graph(
    session: AsyncSession,
    investigation: Investigation,
    max_depth: int,
    max_nodes: int,
) -> tuple[list[GraphNode], list[GraphEdge], bool]:
    links = list(
        (
            await session.scalars(
                select(InvestigationEntity).where(
                    InvestigationEntity.investigation_id == investigation.id
                )
            )
        ).all()
    )
    roles = {link.entity_id: link.role for link in links}
    if investigation.seed_entity_id is not None:
        roles[investigation.seed_entity_id] = "SEED"
    queue: deque[tuple[UUID, int]] = deque((entity_id, 0) for entity_id in roles)
    visited: set[UUID] = set()
    edge_map: dict[UUID, EntityRelationship] = {}
    truncated = False
    while queue:
        entity_id, depth = queue.popleft()
        if entity_id in visited:
            continue
        if len(visited) >= max_nodes:
            truncated = True
            break
        visited.add(entity_id)
        if depth >= max_depth:
            continue
        relationships = list(
            (
                await session.scalars(
                    select(EntityRelationship).where(
                        or_(
                            EntityRelationship.source_entity_id == entity_id,
                            EntityRelationship.target_entity_id == entity_id,
                        )
                    )
                )
            ).all()
        )
        for relationship in relationships:
            edge_map[relationship.id] = relationship
            other = (
                relationship.target_entity_id
                if relationship.source_entity_id == entity_id
                else relationship.source_entity_id
            )
            if other not in visited:
                queue.append((other, depth + 1))
    entities = {
        entity.id: entity
        for entity in (
            await session.scalars(select(Entity).where(Entity.id.in_(visited)))
        ).all()
    } if visited else {}
    nodes = [
        GraphNode(
            id=entity_id,
            entity_type=entities[entity_id].entity_type.value,
            value=entities[entity_id].normalized_value,
            role=roles.get(entity_id, "RELATED"),
        )
        for entity_id in visited
        if entity_id in entities
    ]
    edges = [
        GraphEdge(
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
        for relationship in edge_map.values()
        if relationship.source_entity_id in visited and relationship.target_entity_id in visited
    ]
    return nodes, edges, truncated


async def calculate_similarity(
    session: AsyncSession, investigation: Investigation
) -> list[SimilarityScore]:
    current_ids = set(
        (
            await session.scalars(
                select(InvestigationEntity.entity_id).where(
                    InvestigationEntity.investigation_id == investigation.id
                )
            )
        ).all()
    )
    if investigation.seed_entity_id is not None:
        current_ids.add(investigation.seed_entity_id)
    others = list(
        (
            await session.scalars(
                select(Investigation).where(Investigation.id != investigation.id)
            )
        ).all()
    )
    results: list[SimilarityScore] = []
    for other in others:
        other_ids = set(
            (
                await session.scalars(
                    select(InvestigationEntity.entity_id).where(
                        InvestigationEntity.investigation_id == other.id
                    )
                )
            ).all()
        )
        if other.seed_entity_id is not None:
            other_ids.add(other.seed_entity_id)
        union = current_ids | other_ids
        shared = current_ids & other_ids
        if not union or not shared:
            continue
        entities = list(
            (await session.scalars(select(Entity).where(Entity.id.in_(shared)))).all()
        )
        score = round(len(shared) / len(union), 4)
        persisted = await session.scalar(
            select(SimilarityScore).where(
                SimilarityScore.source_investigation_id == investigation.id,
                SimilarityScore.target_investigation_id == other.id,
            )
        )
        if persisted is None:
            persisted = SimilarityScore(
                source_investigation_id=investigation.id,
                target_investigation_id=other.id,
                score=score,
                shared_factors=[entity.normalized_value for entity in entities],
            )
            session.add(persisted)
        else:
            persisted.score = score
            persisted.shared_factors = [entity.normalized_value for entity in entities]
        results.append(persisted)
    await session.commit()
    return results

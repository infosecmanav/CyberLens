from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.intelligence.connectors.models import ConnectorOutcome
from app.models.enums import CollectionJobStatus, EntityType


class NormalizeRequest(BaseModel):
    value: str = Field(min_length=1, max_length=2048)
    entity_type: EntityType | None = None


class NormalizedEntityResponse(BaseModel):
    entity_type: EntityType
    original_value: str
    normalized_value: str
    attributes: dict[str, object]


class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: EntityType
    value: str
    normalized_value: str
    display_name: str | None
    attributes: dict[str, object]
    created_at: datetime
    updated_at: datetime


class EntityListResponse(BaseModel):
    items: list[EntityResponse]
    total: int
    limit: int
    offset: int


class ObservationResponse(BaseModel):
    id: UUID
    source_id: str
    observation_type: str
    summary: str
    observed_at: datetime
    confidence: float | None
    source_reference: str | None
    attributes: dict[str, object]


class LookupRequest(NormalizeRequest):
    source_ids: list[str] | None = Field(default=None, max_length=20)
    include_demo: bool = False


class LookupSourceResult(BaseModel):
    source_id: str
    outcome: ConnectorOutcome
    message: str | None
    observation_ids: list[UUID] = Field(default_factory=list)
    retry_after_seconds: int | None
    raw_reference: str | None


class LookupResponse(BaseModel):
    job_id: UUID
    status: CollectionJobStatus
    entity: EntityResponse
    results: list[LookupSourceResult]
    completed_at: datetime

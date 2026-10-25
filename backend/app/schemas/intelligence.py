from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

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


class StixBundlePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["bundle"]
    id: str = Field(pattern=r"^bundle--[0-9a-fA-F-]{36}$", max_length=80)
    objects: list[dict[str, Any]] = Field(max_length=500)


class StixBundleImportRequest(BaseModel):
    bundle: StixBundlePayload
    source_reference: HttpUrl | None = None


class StixImportIssue(BaseModel):
    object_index: int
    external_id: str | None
    disposition: Literal["REJECTED", "SKIPPED"]
    code: str
    message: str


class StixImportedObservation(BaseModel):
    entity_id: UUID
    observation_id: UUID
    entity_type: EntityType
    normalized_value: str
    external_id: str
    deduplicated: bool


class StixImportResponse(BaseModel):
    import_id: UUID
    bundle_id: str
    source_id: str
    received_objects: int
    accepted_objects: int
    imported_observations: int
    deduplicated_observations: int
    created_entities: int
    reused_entities: int
    rejected_objects: int
    skipped_objects: int
    completed_at: datetime
    items: list[StixImportedObservation]
    issues: list[StixImportIssue]


class ImportBatchSummary(BaseModel):
    id: UUID
    bundle_id: str
    source_id: str
    format: str
    status: str
    source_reference: str | None
    received_objects: int
    accepted_objects: int
    imported_observations: int
    deduplicated_observations: int
    created_entities: int
    reused_entities: int
    rejected_objects: int
    skipped_objects: int
    created_at: datetime
    completed_at: datetime | None


class ImportBatchListResponse(BaseModel):
    items: list[ImportBatchSummary]
    total: int
    limit: int
    offset: int


class ImportObjectOutcomeResponse(BaseModel):
    id: UUID
    object_index: int
    external_id: str | None
    disposition: str
    code: str
    message: str
    entity_id: UUID | None
    observation_id: UUID | None
    content_hash: str
    raw_record: dict[str, Any]


class ImportBatchDetail(ImportBatchSummary):
    bundle_hash: str
    contract: dict[str, Any]
    objects: list[ImportObjectOutcomeResponse]

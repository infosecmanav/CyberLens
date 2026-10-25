import re
from datetime import datetime
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.intelligence.connectors.models import ConnectorOutcome
from app.models.enums import CollectionJobStatus, EntityType, EvidencePolarity


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


class StixImportFilterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_types: list[EntityType] = Field(default_factory=list, max_length=8)
    minimum_confidence: int | None = Field(default=None, ge=0, le=100)
    valid_from_start: datetime | None = None
    valid_from_end: datetime | None = None
    required_marking_refs: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_definition(self) -> Self:
        supported = {
            EntityType.IPV4,
            EntityType.IPV6,
            EntityType.DOMAIN,
            EntityType.URL,
            EntityType.EMAIL,
            EntityType.MD5,
            EntityType.SHA1,
            EntityType.SHA256,
        }
        if len(set(self.entity_types)) != len(self.entity_types):
            raise ValueError("entity_types must not contain duplicates")
        if not set(self.entity_types).issubset(supported):
            raise ValueError("entity_types contains an unsupported STIX import type")
        for field_name, value in (
            ("valid_from_start", self.valid_from_start),
            ("valid_from_end", self.valid_from_end),
        ):
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{field_name} must include a timezone")
        if (
            self.valid_from_start is not None
            and self.valid_from_end is not None
            and self.valid_from_end < self.valid_from_start
        ):
            raise ValueError("valid_from_end cannot be earlier than valid_from_start")
        if len(set(self.required_marking_refs)) != len(self.required_marking_refs):
            raise ValueError("required_marking_refs must not contain duplicates")
        for marking_ref in self.required_marking_refs:
            if (
                len(marking_ref) > 100
                or re.fullmatch(r"marking-definition--[0-9a-fA-F-]{36}", marking_ref) is None
            ):
                raise ValueError("required_marking_refs must contain STIX marking-definition IDs")
        return self


class StixBundleImportRequest(BaseModel):
    bundle: StixBundlePayload
    source_reference: HttpUrl | None = None
    filters: StixImportFilterRequest = Field(default_factory=StixImportFilterRequest)


class StixImportIssue(BaseModel):
    object_index: int
    external_id: str | None
    disposition: Literal["FILTERED", "REJECTED", "SKIPPED"]
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
    filtered_objects: int
    promoted_objects: int
    filter_definition: dict[str, Any]
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
    filtered_objects: int
    promoted_objects: int
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
    evidence_id: UUID | None
    content_hash: str
    raw_record: dict[str, Any]


class ImportBatchDetail(ImportBatchSummary):
    bundle_hash: str
    contract: dict[str, Any]
    filter_definition: dict[str, Any]
    objects: list[ImportObjectOutcomeResponse]


class EvidencePromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    polarity: EvidencePolarity
    claim: str = Field(min_length=10, max_length=2000)
    uncertainty_notes: str = Field(min_length=10, max_length=2000)

    @field_validator("claim", "uncertainty_notes")
    @classmethod
    def meaningful_text(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 10:
            raise ValueError("promotion text must contain at least 10 non-whitespace characters")
        return stripped


class EvidencePromotionResponse(BaseModel):
    evidence_id: UUID
    import_id: UUID
    object_outcome_id: UUID
    observation_id: UUID
    polarity: EvidencePolarity
    claim: str
    uncertainty_notes: str
    promoted_by: UUID
    analyst_reviewed_at: datetime

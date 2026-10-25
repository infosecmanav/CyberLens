from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.enums import CollectionJobStatus, EntityType


class EnrichmentPolicyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    entity_types: list[EntityType] = Field(min_length=1, max_length=18)
    source_ids: list[str] = Field(min_length=1, max_length=20)
    max_entities_per_run: int = Field(default=25, ge=1, le=100)
    cadence_minutes: int = Field(default=60, ge=10, le=10080)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("entity_types", "source_ids")
    @classmethod
    def unique_values(cls, value: list[object]) -> list[object]:
        if len(value) != len(set(value)):
            raise ValueError("values must not contain duplicates")
        return value


class EnrichmentPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    cadence_minutes: int = Field(ge=10, le=10080)


class EnrichmentPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    entity_types: list[str]
    source_ids: list[str]
    max_entities_per_run: int
    cadence_minutes: int
    enabled: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime

    @field_serializer("next_run_at", "last_run_at", "created_at", when_used="json")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


class EnrichmentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_id: UUID
    collection_job_id: UUID
    status: CollectionJobStatus
    source_outcomes: list[dict[str, object]]
    observation_ids: list[str]
    new_observation_ids: list[str]


class EnrichmentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_id: UUID
    status: CollectionJobStatus
    candidate_entities: int
    processed_entities: int
    new_observations: int
    source_outcomes: dict[str, int]
    error: str | None
    started_at: datetime
    completed_at: datetime | None
    items: list[EnrichmentItemResponse] = Field(default_factory=list)

    @field_serializer("started_at", "completed_at", when_used="json")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")

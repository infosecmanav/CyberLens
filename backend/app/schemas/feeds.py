from datetime import UTC, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.models.enums import CollectionJobStatus
from app.models.intelligence import FeedSubscription


class FeedSubscriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    source_id: str = Field(min_length=2, max_length=80)
    cadence_minutes: int = Field(default=60, ge=10, le=10080)
    max_records: int = Field(default=1000, ge=1, le=5000)

    @field_validator("name", "source_id")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()


class FeedSubscriptionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    cadence_minutes: int = Field(ge=10, le=10080)
    max_records: int = Field(ge=1, le=5000)


class FeedSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_id: str
    enabled: bool
    cadence_minutes: int
    max_records: int
    next_run_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def source_slug(cls, value: object) -> object:
        if isinstance(value, FeedSubscription):
            return {
                "id": value.id,
                "name": value.name,
                "source_id": value.source.source_id,
                "enabled": value.enabled,
                "cadence_minutes": value.cadence_minutes,
                "max_records": value.max_records,
                "next_run_at": value.next_run_at,
                "last_run_at": value.last_run_at,
                "created_at": value.created_at,
            }
        return value

    @field_serializer("next_run_at", "last_run_at", "created_at", when_used="json")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


class FeedRunItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    record_index: int
    external_id: str | None
    disposition: str
    code: str
    message: str
    entity_id: UUID | None
    observation_id: UUID | None
    content_hash: str | None


class FeedRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subscription_id: UUID
    status: CollectionJobStatus
    connector_outcome: str | None
    received_records: int
    accepted_records: int
    rejected_records: int
    created_entities: int
    reused_entities: int
    new_observations: int
    deduplicated_observations: int
    error: str | None
    started_at: datetime
    completed_at: datetime | None
    items: list[FeedRunItemResponse] = Field(default_factory=list)

    @field_serializer("started_at", "completed_at", when_used="json")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")

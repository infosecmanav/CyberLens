from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.intelligence.connectors.models import ConnectorOutcome
from app.models.enums import EntityType, ImplementationStatus, SourceCategory, SourceHealth


class CapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    operation: str
    entity_type: str
    enabled: bool
    notes: str | None


class SourceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: str
    name: str
    category: SourceCategory
    access_method: str
    auth_scheme: str
    implementation_status: ImplementationStatus
    health_status: SourceHealth
    environment_variables: list[str]
    last_checked: datetime | None
    last_success: datetime | None
    last_error: str | None


class SourceDetail(SourceSummary):
    official_url: str | None
    api_documentation_url: str | None
    free_access_status: str
    commercial_usage_status: str
    terms_and_licensing_notes: str | None
    supported_entity_types: list[str]
    supported_operations: list[str]
    rate_limit_policy: dict[str, object]
    caching_policy: dict[str, object]
    attribution_requirements: str | None
    capabilities: list[CapabilityResponse]


class SourceListResponse(BaseModel):
    items: list[SourceSummary]
    total: int
    limit: int
    offset: int


class SourceTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: EntityType
    value: str = Field(min_length=1, max_length=2048)


class SourceHealthResponse(BaseModel):
    source_id: str
    health_status: SourceHealth
    outcome: ConnectorOutcome | None = None
    message: str | None = None
    required_environment_variables: list[str]
    configured_environment_variables: list[str]
    last_checked: datetime | None
    last_success: datetime | None

    @field_serializer("last_checked", "last_success", when_used="json")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")

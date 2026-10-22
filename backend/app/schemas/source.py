from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ImplementationStatus, SourceCategory, SourceHealth


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

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ConnectorOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    NO_RESULT = "NO_RESULT"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    AUTH_FAILED = "AUTH_FAILED"
    FORBIDDEN = "FORBIDDEN"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    SOURCE_ERROR = "SOURCE_ERROR"
    TERMS_RESTRICTED = "TERMS_RESTRICTED"


class ConnectorCapability(BaseModel):
    operation: str
    entity_types: set[str] = Field(default_factory=set)
    requires_authentication: bool = False
    notes: str | None = None


class ConnectorManifest(BaseModel):
    source_id: str
    name: str
    capabilities: list[ConnectorCapability]
    required_environment_variables: list[str] = Field(default_factory=list)
    default_timeout_seconds: float = 10.0
    active_requests_allowed: bool = False


class IntelligenceEntity(BaseModel):
    entity_type: str
    value: str


class ConnectorRequest(BaseModel):
    entity: IntelligenceEntity | None = None
    query: str | None = None
    reference: str | None = None
    cursor: str | None = None


class NormalizedObservation(BaseModel):
    entity: IntelligenceEntity
    observation_type: str
    summary: str
    observed_at: datetime
    source_reference: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    raw_record: dict[str, Any] = Field(default_factory=dict)
    external_id: str | None = None


class ConnectorResult(BaseModel):
    source_id: str
    outcome: ConnectorOutcome
    observations: list[NormalizedObservation] = Field(default_factory=list)
    message: str | None = None
    retry_after_seconds: int | None = None
    quota_remaining: int | None = None
    raw_reference: str | None = None

import re
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

from app.models.enums import ApprovalStatus, ExportStatus


def _validate_markings(values: list[str]) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError("allowed_marking_refs must not contain duplicates")
    for value in values:
        if re.fullmatch(r"marking-definition--[0-9a-fA-F-]{36}", value) is None:
            raise ValueError("marking allowlists must contain STIX marking-definition IDs")
    return values


class ExportPolicyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    collection_id: UUID
    allowed_marking_refs: list[str] = Field(default_factory=list, max_length=100)
    allow_unmarked: bool = False
    max_objects: int = Field(default=100, ge=1, le=500)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("allowed_marking_refs")
    @classmethod
    def valid_markings(cls, value: list[str]) -> list[str]:
        return _validate_markings(value)

    @model_validator(mode="after")
    def requires_scope(self) -> "ExportPolicyCreate":
        if not self.allow_unmarked and not self.allowed_marking_refs:
            raise ValueError(
                "configure at least one allowed marking or explicitly allow unmarked data"
            )
        return self


class ExportPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    allowed_marking_refs: list[str] = Field(default_factory=list, max_length=100)
    allow_unmarked: bool = False
    max_objects: int = Field(default=100, ge=1, le=500)

    @field_validator("allowed_marking_refs")
    @classmethod
    def valid_markings(cls, value: list[str]) -> list[str]:
        return _validate_markings(value)

    @model_validator(mode="after")
    def requires_scope(self) -> "ExportPolicyUpdate":
        if self.enabled and not self.allow_unmarked and not self.allowed_marking_refs:
            raise ValueError("enabled policies require a marking allowlist or unmarked allowance")
        return self


class ExportPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_id: UUID
    name: str
    enabled: bool
    allowed_marking_refs: list[str]
    allow_unmarked: bool
    max_objects: int
    require_approval: bool
    created_by: UUID
    created_at: datetime


class ExportRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: UUID
    evidence_ids: list[UUID] = Field(min_length=1, max_length=500)
    risk_summary: str = Field(min_length=20, max_length=4000)

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("evidence_ids must not contain duplicates")
        return value


class ExportApprovalResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApprovalStatus
    rationale: str = Field(min_length=20, max_length=4000)

    @model_validator(mode="after")
    def final_status(self) -> "ExportApprovalResolve":
        if self.status not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
            raise ValueError("export approval must be APPROVED or REJECTED")
        return self


class EligibleExportEvidence(BaseModel):
    evidence_id: UUID
    entity_id: UUID
    entity_type: str
    normalized_value: str
    claim: str
    polarity: str
    marking_refs: list[str]
    eligible: bool
    reason: str | None


class ExportRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_id: UUID
    approval_id: UUID
    requested_by: UUID
    status: ExportStatus
    evidence_ids: list[str]
    bundle_id: str
    bundle_hash: str
    stix_bundle: dict[str, object]
    object_count: int
    requested_at: datetime
    approved_at: datetime | None
    delivered_at: datetime | None
    delivery_attempts: int
    delivery_receipt: dict[str, object]
    error: str | None

    @field_serializer("requested_at", "approved_at", "delivered_at", when_used="json")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")

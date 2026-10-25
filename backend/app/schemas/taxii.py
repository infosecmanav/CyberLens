import os
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.models.enums import TaxiiRunStatus
from app.models.intelligence import TaxiiServer


def _validate_https_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.query
    ):
        raise ValueError("URL must be an HTTPS endpoint without credentials, query, or fragment")
    return value.rstrip("/") + "/"


class TaxiiServerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    discovery_url: str = Field(min_length=10, max_length=1000)
    auth_environment_variable: str | None = Field(default=None, max_length=120)
    timeout_seconds: int = Field(default=10, ge=2, le=30)
    page_size: int = Field(default=100, ge=1, le=200)
    max_pages: int = Field(default=10, ge=1, le=20)

    @field_validator("discovery_url")
    @classmethod
    def valid_discovery_url(cls, value: str) -> str:
        return _validate_https_url(value)

    @field_validator("auth_environment_variable")
    @classmethod
    def valid_environment_name(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[A-Z][A-Z0-9_]{1,119}", value) is None:
            raise ValueError("auth_environment_variable must be an uppercase environment name")
        return value

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()


class TaxiiCollectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected: bool
    poll_interval_minutes: int = Field(default=60, ge=10, le=10080)


class TaxiiCollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_id: str
    title: str
    description: str | None
    can_read: bool
    can_write: bool
    media_types: list[str]
    selected: bool
    poll_interval_minutes: int
    added_after_cursor: datetime | None
    next_run_at: datetime | None
    last_run_at: datetime | None

    @field_serializer("added_after_cursor", "next_run_at", "last_run_at", when_used="json")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


class TaxiiServerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    discovery_url: str
    api_root_url: str | None
    auth_environment_variable: str | None
    credential_configured: bool
    enabled: bool
    timeout_seconds: int
    page_size: int
    max_pages: int
    discovered_at: datetime | None
    last_error: str | None
    collections: list[TaxiiCollectionResponse]

    @model_validator(mode="before")
    @classmethod
    def add_credential_state(cls, value: object) -> object:
        if isinstance(value, TaxiiServer):
            name = value.auth_environment_variable
            return {
                "id": value.id,
                "name": value.name,
                "discovery_url": value.discovery_url,
                "api_root_url": value.api_root_url,
                "auth_environment_variable": name,
                "credential_configured": bool(name and os.getenv(name)),
                "enabled": value.enabled,
                "timeout_seconds": value.timeout_seconds,
                "page_size": value.page_size,
                "max_pages": value.max_pages,
                "discovered_at": value.discovered_at,
                "last_error": value.last_error,
                "collections": value.collections,
            }
        return value


class TaxiiCollectionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_id: UUID
    status: TaxiiRunStatus
    pages_fetched: int
    manifest_objects: int
    received_objects: int
    accepted_objects: int
    rejected_objects: int
    import_ids: list[str]
    cursor_started_at: datetime | None
    cursor_completed_at: datetime | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None

    @field_serializer(
        "cursor_started_at",
        "cursor_completed_at",
        "started_at",
        "completed_at",
        when_used="json",
    )
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")

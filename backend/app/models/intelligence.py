from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    CollectionJobStatus,
    EntityType,
    EvidencePolarity,
    ImplementationStatus,
    SourceCategory,
    SourceHealth,
)


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    category: Mapped[SourceCategory] = mapped_column(
        Enum(SourceCategory, native_enum=False, length=32), index=True, nullable=False
    )
    official_url: Mapped[str | None] = mapped_column(String(500))
    api_documentation_url: Mapped[str | None] = mapped_column(String(500))
    access_method: Mapped[str] = mapped_column(String(80), default="TO_BE_VERIFIED")
    auth_scheme: Mapped[str] = mapped_column(String(80), default="TO_BE_VERIFIED")
    environment_variables: Mapped[list[str]] = mapped_column(JSON, default=list)
    free_access_status: Mapped[str] = mapped_column(String(120), default="UNVERIFIED")
    commercial_usage_status: Mapped[str] = mapped_column(String(120), default="UNVERIFIED")
    terms_and_licensing_notes: Mapped[str | None] = mapped_column(Text)
    supported_entity_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    supported_operations: Mapped[list[str]] = mapped_column(JSON, default=list)
    rate_limit_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    caching_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attribution_requirements: Mapped[str | None] = mapped_column(Text)
    implementation_status: Mapped[ImplementationStatus] = mapped_column(
        Enum(ImplementationStatus, native_enum=False, length=40),
        default=ImplementationStatus.INVESTIGATION_NEEDED,
        index=True,
        nullable=False,
    )
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    health_status: Mapped[SourceHealth] = mapped_column(
        Enum(SourceHealth, native_enum=False, length=24),
        default=SourceHealth.UNKNOWN,
        nullable=False,
    )

    capabilities: Mapped[list["SourceCapability"]] = relationship(
        back_populates="source", cascade="all, delete-orphan", lazy="selectin"
    )


class SourceCapability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_capabilities"
    __table_args__ = (UniqueConstraint("source_id", "operation", "entity_type"),)

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    operation: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    source: Mapped[Source] = relationship(back_populates="capabilities")


class Entity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("entity_type", "normalized_value"),
        Index("ix_entities_value", "normalized_value"),
    )

    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, native_enum=False, length=32), nullable=False
    )
    value: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(2048), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(500))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class CollectionJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "collection_jobs"

    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[CollectionJobStatus] = mapped_column(
        Enum(CollectionJobStatus, native_enum=False, length=20),
        default=CollectionJobStatus.PENDING,
        index=True,
        nullable=False,
    )
    requested_source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class SourceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint("source_id", "entity_id", "content_hash"),
        Index("ix_source_records_reference", "source_reference"),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(500))
    source_reference: Mapped[str | None] = mapped_column(String(1000))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_record: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Observation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("source_record_id", "observation_type"),)

    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    source_record_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_records.id", ondelete="SET NULL"), index=True
    )
    observation_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[float | None] = mapped_column(Float)
    source_reference: Mapped[str | None] = mapped_column(String(1000))
    upstream_provenance: Mapped[str | None] = mapped_column(String(500))
    raw_record: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Evidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence"

    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    polarity: Mapped[EvidencePolarity] = mapped_column(
        Enum(EvidencePolarity, native_enum=False, length=20), nullable=False
    )
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    uncertainty_notes: Mapped[str | None] = mapped_column(Text)
    analyst_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EntityRelationship(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "entity_relationships"
    __table_args__ = (
        UniqueConstraint("source_entity_id", "target_entity_id", "relationship_type"),
    )

    source_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"), index=True
    )
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[float | None] = mapped_column(Float)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    uncertainty_notes: Mapped[str | None] = mapped_column(Text)


class ImportBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_imports"

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    submitted_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    bundle_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    bundle_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    format: Mapped[str] = mapped_column(String(40), default="STIX_2_1", nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(1000))
    contract: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    filter_definition: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    received_objects: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_objects: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_observations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deduplicated_observations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_entities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reused_entities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_objects: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_objects: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filtered_objects: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    objects: Mapped[list["ImportObjectOutcome"]] = relationship(
        back_populates="import_batch",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ImportObjectOutcome.object_index",
    )


class ImportObjectOutcome(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_import_objects"
    __table_args__ = (UniqueConstraint("import_batch_id", "object_index"),)

    import_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("intelligence_imports.id", ondelete="CASCADE"), index=True, nullable=False
    )
    object_index: Mapped[int] = mapped_column(Integer, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(500))
    disposition: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), index=True
    )
    observation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("observations.id", ondelete="SET NULL"), index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_record: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    import_batch: Mapped[ImportBatch] = relationship(back_populates="objects")


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

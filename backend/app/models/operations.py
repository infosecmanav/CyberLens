from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    ApprovalStatus,
    CasePriority,
    CaseStatus,
    DetectionKind,
    DetectionValidationStatus,
    IntelligenceChangeType,
    InvestigationStatus,
    InvestigationVerdict,
    MonitoringRunStatus,
    MonitoringStatus,
    PlaybookExecutionStatus,
    StepStatus,
    TaskStatus,
)


class Investigation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "investigations"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, native_enum=False, length=32),
        default=InvestigationStatus.PLANNING,
        index=True,
        nullable=False,
    )
    verdict: Mapped[InvestigationVerdict | None] = mapped_column(
        Enum(InvestigationVerdict, native_enum=False, length=32), index=True
    )
    seed_entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), index=True
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list)
    budgets: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    budget_usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    input_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    planner_version: Mapped[str] = mapped_column(String(40), default="deterministic-v1")
    error: Mapped[str | None] = mapped_column(Text)


class InvestigationEntity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "investigation_entities"
    __table_args__ = (UniqueConstraint("investigation_id", "entity_id", "role"),)

    investigation_id: Mapped[UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(40), default="SEED", nullable=False)


class InvestigationStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "investigation_steps"
    __table_args__ = (UniqueConstraint("investigation_id", "idempotency_key"),)

    investigation_id: Mapped[UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, native_enum=False, length=32), nullable=False
    )
    status: Mapped[StepStatus] = mapped_column(
        Enum(StepStatus, native_enum=False, length=20),
        default=StepStatus.PENDING,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    operational_reason: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class InvestigationEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "investigation_events"

    investigation_id: Mapped[UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Finding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "findings"

    investigation_id: Mapped[UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    confidence_dimensions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    uncertainty: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="OPEN", nullable=False)


class FindingEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "finding_evidence"
    __table_args__ = (UniqueConstraint("finding_id", "evidence_id"),)

    finding_id: Mapped[UUID] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dimension: Mapped[str] = mapped_column(String(60), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)


class Assessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessments"

    investigation_id: Mapped[UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), index=True
    )
    assessment_type: Mapped[str] = mapped_column(String(80), nullable=False)
    verdict: Mapped[InvestigationVerdict] = mapped_column(
        Enum(InvestigationVerdict, native_enum=False, length=32), nullable=False
    )
    confidence_dimensions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    methodology: Mapped[str] = mapped_column(String(80), default="HEURISTIC_V1")
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list)
    analyst_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssessmentEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_evidence"
    __table_args__ = (UniqueConstraint("assessment_id", "evidence_id"),)

    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True, nullable=False
    )
    polarity: Mapped[str] = mapped_column(String(20), nullable=False)


class AnalystDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analyst_decisions"

    investigation_id: Mapped[UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    verdict: Mapped[InvestigationVerdict] = mapped_column(
        Enum(InvestigationVerdict, native_enum=False, length=32), nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("analyst_decisions.id", ondelete="SET NULL")
    )


class DetectionCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "detection_candidates"

    investigation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("investigations.id", ondelete="SET NULL"), index=True
    )
    finding_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("findings.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    kind: Mapped[DetectionKind] = mapped_column(
        Enum(DetectionKind, native_enum=False, length=16), index=True, nullable=False
    )
    behavior_hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    technique_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    required_telemetry: Mapped[list[str]] = mapped_column(JSON, default=list)
    field_assumptions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    candidate_logic: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    false_positives: Mapped[list[str]] = mapped_column(JSON, default=list)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list)
    validation_status: Mapped[DetectionValidationStatus] = mapped_column(
        Enum(DetectionValidationStatus, native_enum=False, length=32),
        default=DetectionValidationStatus.DRAFT,
        index=True,
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class DetectionValidation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "detection_validations"

    detection_id: Mapped[UUID] = mapped_column(
        ForeignKey("detection_candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[DetectionValidationStatus] = mapped_column(
        Enum(DetectionValidationStatus, native_enum=False, length=32), nullable=False
    )
    environment: Mapped[str] = mapped_column(String(80), nullable=False)
    validation_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    validated_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Case(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cases"

    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, native_enum=False, length=24),
        default=CaseStatus.OPEN,
        index=True,
        nullable=False,
    )
    priority: Mapped[CasePriority] = mapped_column(
        Enum(CasePriority, native_enum=False, length=16), index=True, nullable=False
    )
    investigation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("investigations.id", ondelete="SET NULL"), index=True
    )
    owner_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CaseTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "case_tasks"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=24),
        default=TaskStatus.OPEN,
        index=True,
        nullable=False,
    )
    owner_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    action_type: Mapped[str] = mapped_column(String(80), default="INTERNAL_TASK")
    high_impact: Mapped[bool] = mapped_column(default=False, nullable=False)
    dry_run: Mapped[bool] = mapped_column(default=True, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CaseEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "case_evidence"
    __table_args__ = (UniqueConstraint("case_id", "evidence_id"),)

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True, nullable=False
    )


class Playbook(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "playbooks"

    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class PlaybookExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "playbook_executions"

    playbook_id: Mapped[UUID] = mapped_column(
        ForeignKey("playbooks.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    case_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"), index=True
    )
    investigation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("investigations.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[PlaybookExecutionStatus] = mapped_column(
        Enum(PlaybookExecutionStatus, native_enum=False, length=24),
        default=PlaybookExecutionStatus.PENDING,
        index=True,
        nullable=False,
    )
    dry_run: Mapped[bool] = mapped_column(default=True, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class ApprovalRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_requests"

    task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("case_tasks.id", ondelete="CASCADE"), index=True
    )
    execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("playbook_executions.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    risk_summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, native_enum=False, length=20),
        default=ApprovalStatus.PENDING,
        index=True,
        nullable=False,
    )
    requested_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    resolved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolution_rationale: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MonitoringObjective(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "monitoring_objectives"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), index=True
    )
    cadence_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[MonitoringStatus] = mapped_column(
        Enum(MonitoringStatus, native_enum=False, length=20),
        default=MonitoringStatus.ACTIVE,
        index=True,
        nullable=False,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_fingerprint: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class MonitoringRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "monitoring_runs"

    objective_id: Mapped[UUID] = mapped_column(
        ForeignKey("monitoring_objectives.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[MonitoringRunStatus] = mapped_column(
        Enum(MonitoringRunStatus, native_enum=False, length=20), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fingerprint: Mapped[str | None] = mapped_column(String(64))
    change_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class IntelligenceChange(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_changes"

    objective_id: Mapped[UUID] = mapped_column(
        ForeignKey("monitoring_objectives.id", ondelete="CASCADE"), index=True, nullable=False
    )
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("monitoring_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    change_type: Mapped[IntelligenceChangeType] = mapped_column(
        Enum(IntelligenceChangeType, native_enum=False, length=32),
        index=True,
        nullable=False,
    )
    entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_actionable: Mapped[bool] = mapped_column(default=False, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SimilarityScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "similarity_scores"
    __table_args__ = (
        UniqueConstraint("source_investigation_id", "target_investigation_id"),
    )

    source_investigation_id: Mapped[UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_investigation_id: Mapped[UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    shared_factors: Mapped[list[str]] = mapped_column(JSON, default=list)
    limitation: Mapped[str] = mapped_column(
        Text, default="Similarity is contextual and does not establish attribution."
    )

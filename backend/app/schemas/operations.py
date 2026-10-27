from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    ApprovalStatus,
    CasePriority,
    CaseStatus,
    DetectionKind,
    DetectionValidationStatus,
    EvidenceDimension,
    IntelligenceChangeType,
    InvestigationStatus,
    InvestigationVerdict,
    MonitoringRunStatus,
    MonitoringStatus,
    PlaybookExecutionStatus,
    StepStatus,
    TaskStatus,
)


class InvestigationBudgets(BaseModel):
    runtime_seconds: int = Field(default=60, ge=1, le=3600)
    api_requests: int = Field(default=10, ge=0, le=100)
    entities: int = Field(default=50, ge=1, le=1000)
    graph_depth: int = Field(default=2, ge=0, le=5)
    pivot_depth: int = Field(default=1, ge=0, le=3)
    reports: int = Field(default=20, ge=0, le=200)
    cost_usd: float = Field(default=0, ge=0, le=0)


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    objective: str = Field(min_length=3, max_length=4000)
    workflow_type: str = Field(default="IOC_INVESTIGATION", min_length=3, max_length=60)
    seed_value: str | None = Field(default=None, max_length=2048)
    seed_entity_type: str | None = None
    source_ids: list[str] | None = Field(default=None, max_length=20)
    include_demo: bool = False
    budgets: InvestigationBudgets = Field(default_factory=InvestigationBudgets)


class InvestigationStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence: int
    phase: InvestigationStatus
    status: StepStatus
    title: str
    operational_reason: str
    attempts: int
    started_at: datetime | None
    completed_at: datetime | None
    output_data: dict[str, object]
    error: str | None


class InvestigationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    occurred_at: datetime
    event_type: str
    message: str
    details: dict[str, object]


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    statement: str
    severity: str
    confidence_dimensions: dict[str, object]
    uncertainty: str
    status: str
    created_at: datetime


class EvidenceResponse(BaseModel):
    id: UUID
    observation_id: UUID
    source_id: str
    polarity: str
    assessment_dimension: EvidenceDimension
    claim: str
    uncertainty_notes: str | None
    observed_at: datetime
    source_reference: str | None


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_type: str
    verdict: InvestigationVerdict
    confidence_dimensions: dict[str, object]
    evidence_reconciliation: dict[str, object]
    methodology: str
    rationale: str
    limitations: list[str]
    analyst_reviewed_at: datetime | None
    created_at: datetime


class AnalystDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    verdict: InvestigationVerdict
    rationale: str
    decided_by: UUID
    decided_at: datetime
    supersedes_id: UUID | None


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    objective: str
    workflow_type: str
    status: InvestigationStatus
    verdict: InvestigationVerdict | None
    seed_entity_id: UUID | None
    created_by: UUID
    started_at: datetime | None
    completed_at: datetime | None
    limitations: list[str]
    budgets: dict[str, object]
    budget_usage: dict[str, object]
    planner_version: str
    error: str | None
    created_at: datetime
    updated_at: datetime


class InvestigationDetail(InvestigationResponse):
    steps: list[InvestigationStepResponse]
    findings: list[FindingResponse]
    assessments: list[AssessmentResponse]
    decisions: list[AnalystDecisionResponse]
    events: list[InvestigationEventResponse]


class InvestigationListResponse(BaseModel):
    items: list[InvestigationResponse]
    total: int
    limit: int
    offset: int


class AnalystDecisionCreate(BaseModel):
    verdict: InvestigationVerdict
    rationale: str = Field(min_length=10, max_length=4000)


class RelationshipCreate(BaseModel):
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str = Field(min_length=2, max_length=100)
    evidence_id: UUID | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    provenance: dict[str, object] = Field(default_factory=dict)
    uncertainty_notes: str = Field(min_length=3, max_length=2000)
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class GraphNode(BaseModel):
    id: UUID
    entity_type: str
    value: str
    role: str


class GraphEdge(BaseModel):
    id: UUID
    source: UUID
    target: UUID
    relationship_type: str
    evidence_id: UUID | None
    confidence: float | None
    provenance: dict[str, object]
    uncertainty_notes: str | None
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class InvestigationGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncated: bool
    max_depth: int
    limitation: str = "Graph relationships are evidence-backed context, not confirmed attribution."


class SimilarityResponse(BaseModel):
    investigation_id: UUID
    score: float
    shared_factors: list[str]
    limitation: str


class DetectionCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    kind: DetectionKind
    investigation_id: UUID | None = None
    finding_id: UUID | None = None
    behavior_hypothesis: str = Field(min_length=10, max_length=4000)
    technique_ids: list[str] = Field(default_factory=list, max_length=30)
    required_telemetry: list[str] = Field(min_length=1, max_length=30)
    field_assumptions: dict[str, object] = Field(default_factory=dict)
    candidate_logic: str = Field(min_length=3, max_length=20000)
    supporting_evidence_ids: list[UUID] = Field(min_length=1, max_length=100)
    false_positives: list[str] = Field(min_length=1, max_length=30)
    limitations: list[str] = Field(min_length=1, max_length=30)


class DetectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID | None
    finding_id: UUID | None
    title: str
    kind: DetectionKind
    behavior_hypothesis: str
    technique_ids: list[str]
    required_telemetry: list[str]
    field_assumptions: dict[str, object]
    candidate_logic: str
    supporting_evidence_ids: list[str]
    false_positives: list[str]
    limitations: list[str]
    validation_status: DetectionValidationStatus
    created_at: datetime


class DetectionValidationCreate(BaseModel):
    status: DetectionValidationStatus
    environment: str = Field(min_length=2, max_length=80)
    validation_evidence: dict[str, object] = Field(default_factory=dict)
    notes: str = Field(min_length=5, max_length=4000)

    @model_validator(mode="after")
    def production_requires_evidence(self) -> "DetectionValidationCreate":
        if (
            self.status == DetectionValidationStatus.VALIDATED_IN_PRODUCTION
            and not self.validation_evidence
        ):
            raise ValueError("Production validation requires recorded validation evidence")
        return self


class CaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    summary: str = Field(min_length=3, max_length=4000)
    priority: CasePriority = CasePriority.MEDIUM
    investigation_id: UUID | None = None
    owner_id: UUID | None = None


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str
    status: CaseStatus
    priority: CasePriority
    investigation_id: UUID | None
    owner_id: UUID | None
    created_by: UUID
    closed_at: datetime | None
    created_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=3, max_length=4000)
    owner_id: UUID | None = None
    due_at: datetime | None = None
    action_type: str = Field(default="INTERNAL_TASK", min_length=2, max_length=80)
    high_impact: bool = False


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    title: str
    description: str
    status: TaskStatus
    owner_id: UUID | None
    due_at: datetime | None
    action_type: str
    high_impact: bool
    dry_run: bool
    completed_at: datetime | None
    created_at: datetime


class ApprovalCreate(BaseModel):
    risk_summary: str = Field(min_length=10, max_length=4000)


class ApprovalResolve(BaseModel):
    status: ApprovalStatus
    rationale: str = Field(min_length=10, max_length=4000)

    @model_validator(mode="after")
    def final_status_only(self) -> "ApprovalResolve":
        if self.status not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
            raise ValueError("Approval resolution must be APPROVED or REJECTED")
        return self


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID | None
    execution_id: UUID | None
    action: str
    risk_summary: str
    status: ApprovalStatus
    requested_by: UUID
    resolved_by: UUID | None
    resolution_rationale: str | None
    resolved_at: datetime | None
    created_at: datetime


class PlaybookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    description: str
    steps: list[dict[str, object]]
    is_active: bool
    version: int


class PlaybookExecutionCreate(BaseModel):
    case_id: UUID | None = None
    investigation_id: UUID | None = None
    dry_run: bool = True


class PlaybookExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    playbook_id: UUID
    case_id: UUID | None
    investigation_id: UUID | None
    status: PlaybookExecutionStatus
    dry_run: bool
    current_step: int
    events: list[dict[str, object]]
    started_at: datetime | None
    completed_at: datetime | None
    started_by: UUID


class MonitoringObjectiveCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    objective: str = Field(min_length=3, max_length=4000)
    entity_id: UUID | None = None
    cadence_minutes: int = Field(default=1440, ge=15, le=525600)


class MonitoringObjectiveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    objective: str
    entity_id: UUID | None
    cadence_minutes: int
    status: MonitoringStatus
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_fingerprint: str | None
    created_by: UUID
    created_at: datetime


class MonitoringRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    objective_id: UUID
    status: MonitoringRunStatus
    started_at: datetime
    completed_at: datetime | None
    fingerprint: str | None
    change_summary: dict[str, object]
    error: str | None


class IntelligenceChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    objective_id: UUID
    run_id: UUID
    change_type: IntelligenceChangeType
    entity_id: UUID | None
    summary: str
    details: dict[str, object]
    is_actionable: bool
    acknowledged_at: datetime | None
    created_at: datetime


class OperationsMetrics(BaseModel):
    source_total: int
    sources_healthy: int
    investigations_total: int
    investigations_running: int
    open_cases: int
    actionable_changes: int
    detection_candidates: int
    validated_detections: int
    demonstration_records: int

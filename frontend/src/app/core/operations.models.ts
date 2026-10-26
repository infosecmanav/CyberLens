export interface InvestigationStep {
  id: string;
  sequence: number;
  phase: string;
  status: string;
  title: string;
  operational_reason: string;
  attempts: number;
  output_data: Record<string, unknown>;
  error: string | null;
}

export interface Finding {
  id: string;
  title: string;
  statement: string;
  severity: string;
  confidence_dimensions: Record<string, unknown>;
  uncertainty: string;
}

export interface SharedUpstreamGroup {
  reference: string;
  sources: string[];
  polarities: string[];
  evidence_count: number;
}

export interface EvidenceReconciliation {
  status: string;
  independence: string;
  summary: string;
  evidence_count: number;
  provider_count: number;
  provenance_group_count: number;
  supporting_evidence: number;
  conflicting_evidence: number;
  contextual_evidence: number;
  supporting_provenance_groups: number;
  conflicting_provenance_groups: number;
  shared_upstream_groups: SharedUpstreamGroup[];
  limitations: string[];
}

export interface Assessment {
  id: string;
  verdict: string;
  confidence_dimensions: Record<string, unknown>;
  evidence_reconciliation?: EvidenceReconciliation;
  methodology: string;
  rationale: string;
  limitations: string[];
}

export interface Investigation {
  id: string;
  title: string;
  objective: string;
  workflow_type: string;
  status: string;
  verdict: string | null;
  seed_entity_id: string | null;
  limitations: string[];
  budgets: Record<string, unknown>;
  budget_usage: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  steps?: InvestigationStep[];
  findings?: Finding[];
  assessments?: Assessment[];
  decisions?: Array<Record<string, unknown>>;
  events?: Array<Record<string, unknown>>;
}

export interface InvestigationList { items: Investigation[]; total: number; limit: number; offset: number; }

export interface Evidence {
  id: string;
  source_id: string;
  polarity: string;
  claim: string;
  uncertainty_notes: string | null;
  observed_at: string;
  source_reference: string | null;
}

export interface GraphNode { id: string; entity_type: string; value: string; role: string; }
export interface GraphEdge { id: string; source: string; target: string; relationship_type: string; evidence_id: string | null; confidence: number | null; provenance: Record<string, unknown>; uncertainty_notes: string | null; first_seen: string | null; last_seen: string | null; }
export interface InvestigationGraph { nodes: GraphNode[]; edges: GraphEdge[]; truncated: boolean; max_depth: number; limitation: string; }
export interface Similarity { investigation_id: string; score: number; shared_factors: string[]; limitation: string; }

export interface Detection {
  id: string;
  title: string;
  kind: string;
  behavior_hypothesis: string;
  technique_ids: string[];
  required_telemetry: string[];
  candidate_logic: string;
  false_positives: string[];
  limitations: string[];
  validation_status: string;
  created_at: string;
}
export interface DetectionCoverage { candidates: number; validated_in_test: number; validated_in_production: number; }

export interface CaseRecord { id: string; title: string; summary: string; status: string; priority: string; investigation_id: string | null; owner_id: string | null; created_at: string; }
export interface CaseTask { id: string; case_id: string; title: string; description: string; status: string; action_type: string; high_impact: boolean; dry_run: boolean; }
export interface ApprovalRequest { id: string; task_id: string | null; execution_id: string | null; action: string; risk_summary: string; status: string; resolution_rationale: string | null; }
export interface Playbook { id: string; slug: string; name: string; description: string; steps: Array<Record<string, unknown>>; is_active: boolean; version: number; }
export interface PlaybookExecution { id: string; playbook_id: string; status: string; dry_run: boolean; current_step: number; events: Array<Record<string, unknown>>; }
export interface MonitoringObjective { id: string; name: string; objective: string; entity_id: string | null; cadence_minutes: number; status: string; last_run_at: string | null; next_run_at: string | null; }
export interface MonitoringRun { id: string; objective_id: string; status: string; fingerprint: string | null; change_summary: Record<string, unknown>; error: string | null; }
export interface IntelligenceChange { id: string; objective_id: string; entity_id: string | null; change_type: string; summary: string; details: Record<string, unknown>; is_actionable: boolean; acknowledged_at: string | null; created_at: string; }
export interface OperationsMetrics { source_total: number; sources_healthy: number; investigations_total: number; investigations_running: number; open_cases: number; actionable_changes: number; detection_candidates: number; validated_detections: number; demonstration_records: number; }
export interface AuditEvent { id: string; occurred_at: string; actor_id: string | null; action: string; object_type: string; object_id: string | null; details: Record<string, unknown>; }

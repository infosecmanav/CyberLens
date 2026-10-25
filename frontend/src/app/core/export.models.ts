export interface ExportPolicy {
  id: string;
  collection_id: string;
  name: string;
  enabled: boolean;
  allowed_marking_refs: string[];
  allow_unmarked: boolean;
  max_objects: number;
  require_approval: boolean;
  created_by: string;
  created_at: string;
}

export interface EligibleExportEvidence {
  evidence_id: string;
  entity_id: string;
  entity_type: string;
  normalized_value: string;
  claim: string;
  polarity: string;
  marking_refs: string[];
  eligible: boolean;
  reason: string | null;
}

export interface ExportRequest {
  id: string;
  policy_id: string;
  approval_id: string;
  requested_by: string;
  status: string;
  evidence_ids: string[];
  bundle_id: string;
  bundle_hash: string;
  stix_bundle: Record<string, unknown>;
  object_count: number;
  requested_at: string;
  approved_at: string | null;
  delivered_at: string | null;
  delivery_attempts: number;
  delivery_receipt: Record<string, unknown>;
  error: string | null;
}

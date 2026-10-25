export interface IntelligenceEntity {
  id: string;
  entity_type: string;
  value: string;
  normalized_value: string;
  display_name: string | null;
  attributes: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface LookupSourceResult {
  source_id: string;
  outcome: string;
  message: string | null;
  observation_ids: string[];
  retry_after_seconds: number | null;
  raw_reference: string | null;
}

export interface LookupResponse {
  job_id: string;
  status: string;
  entity: IntelligenceEntity;
  results: LookupSourceResult[];
  completed_at: string;
}

export interface IntelligenceObservation {
  id: string;
  source_id: string;
  observation_type: string;
  summary: string;
  observed_at: string;
  confidence: number | null;
  source_reference: string | null;
  attributes: Record<string, unknown>;
}

export interface EntityListResponse {
  items: IntelligenceEntity[];
  total: number;
  limit: number;
  offset: number;
}

export interface StixImportIssue {
  object_index: number;
  external_id: string | null;
  disposition: 'REJECTED' | 'SKIPPED';
  code: string;
  message: string;
}

export interface StixImportedObservation {
  entity_id: string;
  observation_id: string;
  entity_type: string;
  normalized_value: string;
  external_id: string;
  deduplicated: boolean;
}

export interface StixImportResponse {
  import_id: string;
  bundle_id: string;
  source_id: string;
  received_objects: number;
  accepted_objects: number;
  imported_observations: number;
  deduplicated_observations: number;
  created_entities: number;
  reused_entities: number;
  rejected_objects: number;
  skipped_objects: number;
  completed_at: string;
  items: StixImportedObservation[];
  issues: StixImportIssue[];
}

export interface ImportBatchSummary {
  id: string;
  bundle_id: string;
  source_id: string;
  format: string;
  status: string;
  source_reference: string | null;
  received_objects: number;
  accepted_objects: number;
  imported_observations: number;
  deduplicated_observations: number;
  created_entities: number;
  reused_entities: number;
  rejected_objects: number;
  skipped_objects: number;
  created_at: string;
  completed_at: string | null;
}

export interface ImportObjectOutcome {
  id: string;
  object_index: number;
  external_id: string | null;
  disposition: string;
  code: string;
  message: string;
  entity_id: string | null;
  observation_id: string | null;
  content_hash: string;
  raw_record: Record<string, unknown>;
}

export interface ImportBatchDetail extends ImportBatchSummary {
  bundle_hash: string;
  contract: Record<string, unknown>;
  objects: ImportObjectOutcome[];
}

export interface ImportBatchListResponse {
  items: ImportBatchSummary[];
  total: number;
  limit: number;
  offset: number;
}

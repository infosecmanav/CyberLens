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

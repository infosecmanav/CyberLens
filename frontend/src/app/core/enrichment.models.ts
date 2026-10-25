export interface EnrichmentPolicy {
  id: string;
  name: string;
  entity_types: string[];
  source_ids: string[];
  max_entities_per_run: number;
  cadence_minutes: number;
  enabled: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  created_at: string;
}

export interface EnrichmentItem {
  id: string;
  entity_id: string;
  collection_job_id: string;
  status: string;
  source_outcomes: Array<Record<string, unknown>>;
  observation_ids: string[];
  new_observation_ids: string[];
}

export interface EnrichmentRun {
  id: string;
  policy_id: string;
  status: string;
  candidate_entities: number;
  processed_entities: number;
  new_observations: number;
  source_outcomes: Record<string, number>;
  error: string | null;
  started_at: string;
  completed_at: string | null;
  items: EnrichmentItem[];
}

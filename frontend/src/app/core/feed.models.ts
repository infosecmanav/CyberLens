export interface FeedSubscription {
  id: string;
  name: string;
  source_id: string;
  enabled: boolean;
  cadence_minutes: number;
  max_records: number;
  next_run_at: string | null;
  last_run_at: string | null;
  created_at: string;
}

export interface FeedRunItem {
  id: string;
  record_index: number;
  external_id: string | null;
  disposition: string;
  code: string;
  message: string;
  entity_id: string | null;
  observation_id: string | null;
  content_hash: string | null;
}

export interface FeedRun {
  id: string;
  subscription_id: string;
  status: string;
  connector_outcome: string | null;
  received_records: number;
  accepted_records: number;
  rejected_records: number;
  created_entities: number;
  reused_entities: number;
  new_observations: number;
  deduplicated_observations: number;
  error: string | null;
  started_at: string;
  completed_at: string | null;
  items: FeedRunItem[];
}

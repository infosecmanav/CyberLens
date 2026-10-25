export interface TaxiiCollection {
  id: string;
  collection_id: string;
  title: string;
  description: string | null;
  can_read: boolean;
  can_write: boolean;
  media_types: string[];
  selected: boolean;
  poll_interval_minutes: number;
  added_after_cursor: string | null;
  next_run_at: string | null;
  last_run_at: string | null;
}

export interface TaxiiServer {
  id: string;
  name: string;
  discovery_url: string;
  api_root_url: string | null;
  auth_environment_variable: string | null;
  credential_configured: boolean;
  enabled: boolean;
  timeout_seconds: number;
  page_size: number;
  max_pages: number;
  discovered_at: string | null;
  last_error: string | null;
  collections: TaxiiCollection[];
}

export interface TaxiiCollectionRun {
  id: string;
  collection_id: string;
  status: string;
  pages_fetched: number;
  manifest_objects: number;
  received_objects: number;
  accepted_objects: number;
  rejected_objects: number;
  import_ids: string[];
  cursor_started_at: string | null;
  cursor_completed_at: string | null;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

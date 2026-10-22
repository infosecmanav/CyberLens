export interface SourceSummary {
  id: string; source_id: string; name: string; category: string; access_method: string;
  auth_scheme: string; implementation_status: string; health_status: string;
  environment_variables: string[]; last_checked: string | null; last_success: string | null; last_error: string | null;
}
export interface SourceListResponse { items: SourceSummary[]; total: number; limit: number; offset: number; }

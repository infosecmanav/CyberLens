export interface SourceSummary {
  id: string; source_id: string; name: string; category: string; access_method: string;
  auth_scheme: string; implementation_status: string; health_status: string;
  environment_variables: string[]; last_checked: string | null; last_success: string | null; last_error: string | null;
}
export interface SourceListResponse { items: SourceSummary[]; total: number; limit: number; offset: number; }
export interface SourceCapability { operation: string; entity_type: string; enabled: boolean; notes: string | null; }
export interface SourceDetail extends SourceSummary {
  official_url: string | null; api_documentation_url: string | null; free_access_status: string;
  commercial_usage_status: string; terms_and_licensing_notes: string | null;
  supported_entity_types: string[]; supported_operations: string[];
  rate_limit_policy: Record<string, unknown>; caching_policy: Record<string, unknown>;
  attribution_requirements: string | null; capabilities: SourceCapability[];
}

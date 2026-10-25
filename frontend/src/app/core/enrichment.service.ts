import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { EnrichmentPolicy, EnrichmentRun } from './enrichment.models';

@Injectable({ providedIn: 'root' })
export class EnrichmentService {
  private readonly http = inject(HttpClient);

  policies(): Observable<EnrichmentPolicy[]> {
    return this.http.get<EnrichmentPolicy[]>('/api/v1/enrichment/policies');
  }

  create(payload: Record<string, unknown>): Observable<EnrichmentPolicy> {
    return this.http.post<EnrichmentPolicy>('/api/v1/enrichment/policies', payload);
  }

  configure(
    policyId: string,
    enabled: boolean,
    cadenceMinutes: number,
  ): Observable<EnrichmentPolicy> {
    return this.http.put<EnrichmentPolicy>(`/api/v1/enrichment/policies/${policyId}`, {
      enabled,
      cadence_minutes: cadenceMinutes,
    });
  }

  run(policyId: string): Observable<EnrichmentRun> {
    return this.http.post<EnrichmentRun>(
      `/api/v1/enrichment/policies/${policyId}/run`,
      {},
    );
  }

  runs(): Observable<EnrichmentRun[]> {
    return this.http.get<EnrichmentRun[]>('/api/v1/enrichment/runs');
  }
}

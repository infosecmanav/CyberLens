import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { EligibleExportEvidence, ExportPolicy, ExportRequest } from './export.models';

@Injectable({ providedIn: 'root' })
export class ExportService {
  private readonly http = inject(HttpClient);

  policies(): Observable<ExportPolicy[]> {
    return this.http.get<ExportPolicy[]>('/api/v1/exports/policies');
  }

  createPolicy(payload: Record<string, unknown>): Observable<ExportPolicy> {
    return this.http.post<ExportPolicy>('/api/v1/exports/policies', payload);
  }

  configurePolicy(policyId: string, payload: Record<string, unknown>): Observable<ExportPolicy> {
    return this.http.put<ExportPolicy>(`/api/v1/exports/policies/${policyId}`, payload);
  }

  eligibleEvidence(policyId: string): Observable<EligibleExportEvidence[]> {
    const params = new HttpParams().set('policy_id', policyId);
    return this.http.get<EligibleExportEvidence[]>('/api/v1/exports/eligible-evidence', {
      params,
    });
  }

  requests(): Observable<ExportRequest[]> {
    return this.http.get<ExportRequest[]>('/api/v1/exports/requests');
  }

  request(payload: Record<string, unknown>): Observable<ExportRequest> {
    return this.http.post<ExportRequest>('/api/v1/exports/requests', payload);
  }

  resolve(
    exportId: string,
    status: 'APPROVED' | 'REJECTED',
    rationale: string,
  ): Observable<ExportRequest> {
    return this.http.post<ExportRequest>(`/api/v1/exports/requests/${exportId}/resolve`, {
      status,
      rationale,
    });
  }

  deliver(exportId: string): Observable<ExportRequest> {
    return this.http.post<ExportRequest>(`/api/v1/exports/requests/${exportId}/deliver`, {});
  }
}

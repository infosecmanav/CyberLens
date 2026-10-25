import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  EntityListResponse,
  EvidencePromotionPayload,
  EvidencePromotionResponse,
  ImportBatchDetail,
  ImportBatchListResponse,
  IntelligenceObservation,
  LookupResponse,
  StixImportFilterDefinition,
  StixImportResponse,
} from './intelligence.models';

export interface LookupPayload {
  value: string;
  entity_type?: string;
  include_demo: boolean;
}

export interface StixImportPayload {
  bundle: Record<string, unknown>;
  source_reference?: string;
  filters?: StixImportFilterDefinition;
}

@Injectable({ providedIn: 'root' })
export class IntelligenceService {
  private readonly http = inject(HttpClient);

  lookup(payload: LookupPayload): Observable<LookupResponse> {
    return this.http.post<LookupResponse>('/api/v1/intelligence/lookup', payload);
  }

  importStix(payload: StixImportPayload): Observable<StixImportResponse> {
    return this.http.post<StixImportResponse>(
      '/api/v1/intelligence/imports/stix-bundles',
      payload,
    );
  }

  imports(hasIssues?: boolean, hasPromotions?: boolean): Observable<ImportBatchListResponse> {
    let params = new HttpParams().set('limit', 8);
    if (hasIssues !== undefined) params = params.set('has_issues', hasIssues);
    if (hasPromotions !== undefined) params = params.set('has_promotions', hasPromotions);
    return this.http.get<ImportBatchListResponse>('/api/v1/intelligence/imports', { params });
  }

  importDetail(importId: string): Observable<ImportBatchDetail> {
    return this.http.get<ImportBatchDetail>(`/api/v1/intelligence/imports/${importId}`);
  }

  promoteImportObject(
    importId: string,
    objectOutcomeId: string,
    payload: EvidencePromotionPayload,
  ): Observable<EvidencePromotionResponse> {
    return this.http.post<EvidencePromotionResponse>(
      `/api/v1/intelligence/imports/${importId}/objects/${objectOutcomeId}/promote`,
      payload,
    );
  }

  observations(entityId: string): Observable<IntelligenceObservation[]> {
    return this.http.get<IntelligenceObservation[]>(
      `/api/v1/intelligence/entities/${entityId}/observations`,
    );
  }

  recent(): Observable<EntityListResponse> {
    return this.http.get<EntityListResponse>('/api/v1/intelligence/entities', {
      params: { limit: 8 },
    });
  }
}

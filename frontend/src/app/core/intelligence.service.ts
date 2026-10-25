import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  EntityListResponse,
  IntelligenceObservation,
  LookupResponse,
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

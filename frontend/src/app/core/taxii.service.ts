import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { TaxiiCollection, TaxiiCollectionRun, TaxiiServer } from './taxii.models';

@Injectable({ providedIn: 'root' })
export class TaxiiService {
  private readonly http = inject(HttpClient);

  servers(): Observable<TaxiiServer[]> {
    return this.http.get<TaxiiServer[]>('/api/v1/taxii/servers');
  }

  create(payload: Record<string, unknown>): Observable<TaxiiServer> {
    return this.http.post<TaxiiServer>('/api/v1/taxii/servers', payload);
  }

  discover(serverId: string): Observable<TaxiiServer> {
    return this.http.post<TaxiiServer>(`/api/v1/taxii/servers/${serverId}/discover`, {});
  }

  configureCollection(
    collectionId: string,
    selected: boolean,
    pollIntervalMinutes: number,
  ): Observable<TaxiiCollection> {
    return this.http.put<TaxiiCollection>(`/api/v1/taxii/collections/${collectionId}`, {
      selected,
      poll_interval_minutes: pollIntervalMinutes,
    });
  }

  run(collectionId: string): Observable<TaxiiCollectionRun> {
    return this.http.post<TaxiiCollectionRun>(
      `/api/v1/taxii/collections/${collectionId}/run`,
      {},
    );
  }

  runs(): Observable<TaxiiCollectionRun[]> {
    return this.http.get<TaxiiCollectionRun[]>('/api/v1/taxii/runs');
  }
}

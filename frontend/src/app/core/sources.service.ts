import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { SourceDetail, SourceListResponse } from './source.models';

@Injectable({ providedIn: 'root' })
export class SourcesService {
  private readonly http = inject(HttpClient);
  list(category?: string): Observable<SourceListResponse> {
    let params = new HttpParams().set('limit', 200);
    if (category) params = params.set('category', category);
    return this.http.get<SourceListResponse>('/api/v1/sources', { params });
  }
  detail(sourceId: string): Observable<SourceDetail> { return this.http.get<SourceDetail>(`/api/v1/sources/${sourceId}`); }
}

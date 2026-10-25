import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { FeedRun, FeedSubscription } from './feed.models';

@Injectable({ providedIn: 'root' })
export class FeedService {
  private readonly http = inject(HttpClient);

  subscriptions(): Observable<FeedSubscription[]> {
    return this.http.get<FeedSubscription[]>('/api/v1/feeds/subscriptions');
  }

  create(payload: Record<string, unknown>): Observable<FeedSubscription> {
    return this.http.post<FeedSubscription>('/api/v1/feeds/subscriptions', payload);
  }

  configure(
    subscriptionId: string,
    enabled: boolean,
    cadenceMinutes: number,
    maxRecords: number,
  ): Observable<FeedSubscription> {
    return this.http.put<FeedSubscription>(`/api/v1/feeds/subscriptions/${subscriptionId}`, {
      enabled,
      cadence_minutes: cadenceMinutes,
      max_records: maxRecords,
    });
  }

  run(subscriptionId: string): Observable<FeedRun> {
    return this.http.post<FeedRun>(`/api/v1/feeds/subscriptions/${subscriptionId}/run`, {});
  }

  runs(): Observable<FeedRun[]> {
    return this.http.get<FeedRun[]>('/api/v1/feeds/runs');
  }
}

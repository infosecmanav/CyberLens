import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { IntelligenceService } from './intelligence.service';

describe('IntelligenceService', () => {
  let service: IntelligenceService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(IntelligenceService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('submits a lookup to the persisted intelligence endpoint', () => {
    service.lookup({ value: 'CVE-2021-44228', include_demo: false }).subscribe();
    const request = http.expectOne('/api/v1/intelligence/lookup');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ value: 'CVE-2021-44228', include_demo: false });
    request.flush({
      job_id: 'job', status: 'COMPLETED', completed_at: '2026-10-22T00:00:00Z',
      entity: {
        id: 'entity', entity_type: 'CVE', value: 'CVE-2021-44228',
        normalized_value: 'CVE-2021-44228', display_name: 'CVE-2021-44228', attributes: {},
        created_at: '2026-10-22T00:00:00Z', updated_at: '2026-10-22T00:00:00Z',
      },
      results: [],
    });
  });

  it('loads observations for a canonical entity', () => {
    service.observations('entity-id').subscribe();
    const request = http.expectOne('/api/v1/intelligence/entities/entity-id/observations');
    expect(request.request.method).toBe('GET');
    request.flush([]);
  });
});

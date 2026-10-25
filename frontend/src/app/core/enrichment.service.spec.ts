import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { EnrichmentService } from './enrichment.service';

describe('EnrichmentService', () => {
  let service: EnrichmentService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(EnrichmentService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('creates a bounded source and entity allowlist', () => {
    const payload = {
      name: 'Vulnerability context',
      entity_types: ['CVE'],
      source_ids: ['cisa-kev', 'osv'],
      max_entities_per_run: 25,
      cadence_minutes: 60,
    };
    service.create(payload).subscribe();
    const request = http.expectOne('/api/v1/enrichment/policies');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(payload);
    request.flush({});
  });

  it('pauses and manually runs a policy', () => {
    service.configure('policy-id', false, 60).subscribe();
    const configure = http.expectOne('/api/v1/enrichment/policies/policy-id');
    expect(configure.request.method).toBe('PUT');
    expect(configure.request.body).toEqual({ enabled: false, cadence_minutes: 60 });
    configure.flush({});

    service.run('policy-id').subscribe();
    const run = http.expectOne('/api/v1/enrichment/policies/policy-id/run');
    expect(run.request.method).toBe('POST');
    run.flush({});
  });
});

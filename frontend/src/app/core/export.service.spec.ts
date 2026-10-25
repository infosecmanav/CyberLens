import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ExportService } from './export.service';

describe('ExportService', () => {
  let service: ExportService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ExportService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('creates a disabled destination policy with an explicit marking allowlist', () => {
    const payload = {
      name: 'Partner sharing',
      collection_id: 'collection-id',
      allowed_marking_refs: ['marking-definition--fixture'],
      allow_unmarked: false,
      max_objects: 20,
    };
    service.createPolicy(payload).subscribe();
    const request = http.expectOne('/api/v1/exports/policies');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(payload);
    request.flush({});
  });

  it('requests, independently resolves, and delivers a frozen export', () => {
    service.request({
      policy_id: 'policy-id',
      evidence_ids: ['evidence-id'],
      risk_summary: 'Reviewed destination and markings.',
    }).subscribe();
    expect(http.expectOne('/api/v1/exports/requests').request.method).toBe('POST');

    service.resolve('export-id', 'APPROVED', 'Independent review completed.').subscribe();
    const resolve = http.expectOne('/api/v1/exports/requests/export-id/resolve');
    expect(resolve.request.body).toEqual({
      status: 'APPROVED',
      rationale: 'Independent review completed.',
    });

    service.deliver('export-id').subscribe();
    expect(http.expectOne('/api/v1/exports/requests/export-id/deliver').request.method).toBe('POST');
  });
});

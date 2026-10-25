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

  it('submits a manual STIX bundle through the authenticated intelligence API', () => {
    const bundle = {
      type: 'bundle',
      id: 'bundle--11111111-1111-4111-8111-111111111111',
      objects: [],
    };
    const filters = { entity_types: ['DOMAIN'], minimum_confidence: 70 };
    service.importStix({
      bundle,
      source_reference: 'https://example.test/collection',
      filters,
    }).subscribe();
    const request = http.expectOne('/api/v1/intelligence/imports/stix-bundles');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      bundle,
      source_reference: 'https://example.test/collection',
      filters,
    });
    request.flush({
      import_id: 'import-id',
      bundle_id: bundle.id,
      source_id: 'manual-stix-2-1',
      received_objects: 0,
      accepted_objects: 0,
      imported_observations: 0,
      deduplicated_observations: 0,
      created_entities: 0,
      reused_entities: 0,
      rejected_objects: 0,
      skipped_objects: 0,
      filtered_objects: 0,
      filter_definition: filters,
      completed_at: '2026-10-25T00:00:00Z',
      items: [],
      issues: [],
    });
  });

  it('loads import history and a persisted object-outcome report', () => {
    service.imports(true).subscribe();
    const history = http.expectOne(
      (request) => request.url === '/api/v1/intelligence/imports'
        && request.params.get('limit') === '8'
        && request.params.get('has_issues') === 'true',
    );
    expect(history.request.method).toBe('GET');
    history.flush({ items: [], total: 0, limit: 8, offset: 0 });

    service.importDetail('import-id').subscribe();
    const detail = http.expectOne('/api/v1/intelligence/imports/import-id');
    expect(detail.request.method).toBe('GET');
    detail.flush({
      id: 'import-id',
      bundle_id: 'bundle--11111111-1111-4111-8111-111111111111',
      bundle_hash: 'a'.repeat(64),
      source_id: 'manual-stix-2-1',
      format: 'STIX_2_1',
      status: 'COMPLETED',
      source_reference: null,
      contract: {},
      received_objects: 0,
      accepted_objects: 0,
      imported_observations: 0,
      deduplicated_observations: 0,
      created_entities: 0,
      reused_entities: 0,
      rejected_objects: 0,
      skipped_objects: 0,
      filtered_objects: 0,
      filter_definition: {},
      created_at: '2026-10-25T00:00:00Z',
      completed_at: '2026-10-25T00:00:00Z',
      objects: [],
    });
  });
});

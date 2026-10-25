import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { TaxiiService } from './taxii.service';

describe('TaxiiService', () => {
  let service: TaxiiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(TaxiiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('creates and discovers an explicit TAXII relationship', () => {
    const payload = {
      name: 'Partner exchange',
      discovery_url: 'https://taxii.example.test/taxii2/',
      auth_environment_variable: 'PARTNER_TAXII_TOKEN',
    };
    service.create(payload).subscribe();
    const create = http.expectOne('/api/v1/taxii/servers');
    expect(create.request.method).toBe('POST');
    expect(create.request.body).toEqual(payload);
    create.flush({});

    service.discover('server-id').subscribe();
    const discover = http.expectOne('/api/v1/taxii/servers/server-id/discover');
    expect(discover.request.method).toBe('POST');
    discover.flush({});
  });

  it('authorizes and runs a collection through bounded endpoints', () => {
    service.configureCollection('collection-id', true, 60).subscribe();
    const configure = http.expectOne('/api/v1/taxii/collections/collection-id');
    expect(configure.request.method).toBe('PUT');
    expect(configure.request.body).toEqual({ selected: true, poll_interval_minutes: 60 });
    configure.flush({});

    service.run('collection-id').subscribe();
    const run = http.expectOne('/api/v1/taxii/collections/collection-id/run');
    expect(run.request.method).toBe('POST');
    run.flush({});
  });
});

import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { SourcesService } from './sources.service';

describe('SourcesService', () => {
  let service: SourcesService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(SourcesService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads the complete bounded source registry', () => {
    service.list().subscribe();
    const request = http.expectOne(
      (candidate) => candidate.url === '/api/v1/sources' && candidate.params.get('limit') === '200',
    );
    expect(request.request.method).toBe('GET');
    request.flush({ items: [], total: 0, limit: 200, offset: 0 });
  });

  it('runs an explicit typed connection test', () => {
    service.test('virustotal', 'DOMAIN', 'example.test').subscribe();
    const request = http.expectOne('/api/v1/sources/virustotal/test');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ entity_type: 'DOMAIN', value: 'example.test' });
    request.flush({});
  });
});

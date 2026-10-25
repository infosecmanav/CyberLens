import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { FeedService } from './feed.service';

describe('FeedService', () => {
  let service: FeedService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(FeedService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('creates a bounded scheduled feed', () => {
    const payload = {
      name: 'Official CISA KEV',
      source_id: 'cisa-kev',
      cadence_minutes: 60,
      max_records: 1000,
    };
    service.create(payload).subscribe();
    const request = http.expectOne('/api/v1/feeds/subscriptions');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(payload);
    request.flush({});
  });

  it('pauses and manually runs a subscription', () => {
    service.configure('feed-id', false, 120, 500).subscribe();
    const configure = http.expectOne('/api/v1/feeds/subscriptions/feed-id');
    expect(configure.request.method).toBe('PUT');
    expect(configure.request.body).toEqual({
      enabled: false,
      cadence_minutes: 120,
      max_records: 500,
    });
    configure.flush({});

    service.run('feed-id').subscribe();
    const run = http.expectOne('/api/v1/feeds/subscriptions/feed-id/run');
    expect(run.request.method).toBe('POST');
    run.flush({});
  });
});

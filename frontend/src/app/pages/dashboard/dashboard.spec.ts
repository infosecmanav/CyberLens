import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Dashboard } from './dashboard';

describe('Dashboard', () => {
  let fixture: ComponentFixture<Dashboard>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Dashboard],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Dashboard);
    fixture.detectChanges();
  });

  afterEach(() => {
    http.verify();
    fixture.destroy();
  });

  function flushSources(): void {
    http.expectOne((request) => request.url === '/api/v1/sources' && request.params.get('limit') === '200')
      .flush({ items: [], total: 0, limit: 200, offset: 0 });
  }

  it('renders posture percentages from observed metrics', () => {
    flushSources();
    http.expectOne('/api/v1/operations/metrics').flush({
      source_total: 4,
      sources_healthy: 3,
      investigations_total: 4,
      investigations_running: 2,
      open_cases: 1,
      actionable_changes: 2,
      detection_candidates: 4,
      validated_detections: 2,
      demonstration_records: 0,
    });
    fixture.detectChanges();

    const values = [...fixture.nativeElement.querySelectorAll('.posture-ring strong')]
      .map((element: Element) => element.textContent?.trim());
    expect(values).toEqual(['75', '50', '50']);
    expect(fixture.nativeElement.querySelector('.hero-status span')?.textContent).toContain('LIVE');
  });

  it('shows an explicit unavailable state when metrics fail', () => {
    flushSources();
    http.expectOne('/api/v1/operations/metrics').flush('unavailable', { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.hero-status span')?.textContent).toContain('UNAVAILABLE');
    expect(fixture.nativeElement.querySelector('.live-pill')?.textContent).toContain('Telemetry unavailable');
  });
});

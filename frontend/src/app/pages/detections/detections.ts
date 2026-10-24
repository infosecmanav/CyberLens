import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { Detection, DetectionCoverage } from '../../core/operations.models';
import { OperationsService } from '../../core/operations.service';

@Component({ selector: 'app-detections', imports: [RouterLink], templateUrl: './detections.html', styleUrl: './detections.scss' })
export class Detections {
  protected readonly auth = inject(AuthService);
  private readonly operations = inject(OperationsService);
  protected readonly items = signal<Detection[]>([]);
  protected readonly coverage = signal<DetectionCoverage | null>(null);
  protected readonly title = signal('');
  protected readonly hypothesis = signal('');
  protected readonly evidenceId = signal('');
  protected readonly kind = signal('SIGMA');
  protected readonly telemetry = signal('DNS query logs');
  protected readonly technique = signal('');
  protected readonly logic = signal('');
  protected readonly error = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);
  protected readonly loading = signal(false);

  constructor() { this.reload(); }

  protected update(field: 'title' | 'hypothesis' | 'evidence' | 'kind' | 'telemetry' | 'technique' | 'logic', event: Event): void {
    const value = (event.target as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement).value;
    if (field === 'title') this.title.set(value);
    if (field === 'hypothesis') this.hypothesis.set(value);
    if (field === 'evidence') this.evidenceId.set(value);
    if (field === 'kind') this.kind.set(value);
    if (field === 'telemetry') this.telemetry.set(value);
    if (field === 'technique') this.technique.set(value);
    if (field === 'logic') this.logic.set(value);
  }

  protected create(event: Event): void {
    event.preventDefault(); this.loading.set(true); this.error.set(null); this.message.set(null);
    this.operations.createDetection({
      title: this.title(), kind: this.kind(), behavior_hypothesis: this.hypothesis(),
      technique_ids: this.split(this.technique()), required_telemetry: this.split(this.telemetry()),
      candidate_logic: this.logic(), supporting_evidence_ids: [this.evidenceId()],
      false_positives: ['Requires environment-specific tuning'],
      limitations: ['Candidate only until validated against representative telemetry'],
    }).subscribe({
      next: () => { this.loading.set(false); this.message.set('Evidence-backed candidate created.'); this.title.set(''); this.hypothesis.set(''); this.evidenceId.set(''); this.logic.set(''); this.reload(); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected validate(item: Detection): void {
    this.loading.set(true); this.error.set(null);
    this.operations.validateDetection(item.id, { status: 'VALIDATED_IN_TEST', environment: 'analyst-test', validation_evidence: { analyst_review: true }, notes: 'Validated by an analyst in the isolated test environment.' }).subscribe({
      next: () => { this.loading.set(false); this.message.set('Test validation recorded with its environment.'); this.reload(); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected friendly(value: string): string { return value.replaceAll('_', ' ').toLowerCase(); }
  private split(value: string): string[] { return value.split(',').map((item) => item.trim()).filter(Boolean); }
  private reload(): void {
    this.operations.detections().subscribe({ next: (items) => this.items.set(items), error: () => this.error.set('Detection candidates could not be loaded.') });
    this.operations.detectionCoverage().subscribe({ next: (coverage) => this.coverage.set(coverage) });
  }
  private failed(response: HttpErrorResponse): void { this.loading.set(false); this.error.set(typeof response.error?.detail === 'string' ? response.error.detail : 'The detection request failed.'); }
}

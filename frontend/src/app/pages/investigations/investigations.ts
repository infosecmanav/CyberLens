import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import {
  Evidence,
  EvidenceReconciliation,
  Investigation,
  Similarity,
} from '../../core/operations.models';
import { OperationsService } from '../../core/operations.service';

@Component({ selector: 'app-investigations', imports: [DatePipe, RouterLink], templateUrl: './investigations.html', styleUrl: './investigations.scss' })
export class Investigations {
  protected readonly auth = inject(AuthService);
  private readonly operations = inject(OperationsService);
  protected readonly items = signal<Investigation[]>([]);
  protected readonly selected = signal<Investigation | null>(null);
  protected readonly evidence = signal<Evidence[]>([]);
  protected readonly similar = signal<Similarity[]>([]);
  protected readonly title = signal('');
  protected readonly objective = signal('');
  protected readonly seed = signal('');
  protected readonly includeDemo = signal(false);
  protected readonly workflow = signal('IOC_INVESTIGATION');
  protected readonly decisionVerdict = signal('UNKNOWN');
  protected readonly decisionRationale = signal('');
  protected readonly activeTab = signal('overview');
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly reconciliation = computed<EvidenceReconciliation | null>(() => {
    const value = this.selected()?.assessments?.[0]?.evidence_reconciliation;
    return value?.status ? value : null;
  });
  protected readonly tabs = ['overview', 'findings', 'evidence', 'timeline', 'ATT&CK', 'similar', 'detections', 'actions'];
  protected readonly workflows = ['IOC_INVESTIGATION', 'IP_DOMAIN_INVESTIGATION', 'PHISHING_URL_INVESTIGATION', 'MALWARE_HASH_INVESTIGATION', 'CVE_INVESTIGATION', 'ALERT_INVESTIGATION', 'CAMPAIGN_INVESTIGATION', 'INDUSTRY_TIMEFRAME_INVESTIGATION'];

  constructor() { this.reload(); }

  protected update(field: 'title' | 'objective' | 'seed' | 'workflow' | 'decisionVerdict' | 'decisionRationale', event: Event): void {
    const value = (event.target as HTMLInputElement | HTMLTextAreaElement).value;
    if (field === 'title') this.title.set(value);
    if (field === 'objective') this.objective.set(value);
    if (field === 'seed') this.seed.set(value);
    if (field === 'workflow') this.workflow.set(value);
    if (field === 'decisionVerdict') this.decisionVerdict.set(value);
    if (field === 'decisionRationale') this.decisionRationale.set(value);
  }

  protected toggleDemo(event: Event): void { this.includeDemo.set((event.target as HTMLInputElement).checked); }

  protected create(event: Event): void {
    event.preventDefault();
    this.loading.set(true);
    this.error.set(null);
    this.operations.createInvestigation({
      title: this.title(),
      objective: this.objective(),
      workflow_type: this.workflow(),
      ...(this.seed().trim() ? { seed_value: this.seed().trim() } : {}),
      include_demo: this.includeDemo(),
      ...(this.includeDemo() ? { source_ids: ['local-fixtures'] } : {}),
    }).subscribe({
      next: (item) => {
        this.loading.set(false);
        this.selected.set(item);
        this.title.set(''); this.objective.set(''); this.seed.set('');
        this.reload();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected select(item: Investigation): void {
    this.operations.investigation(item.id).subscribe({
      next: (detail) => { this.selected.set(detail); this.loadEvidence(detail.id); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected run(): void {
    const item = this.selected(); if (!item) return;
    this.loading.set(true);
    this.operations.runInvestigation(item.id).subscribe({
      next: (detail) => { this.loading.set(false); this.selected.set(detail); this.loadEvidence(detail.id); this.reload(); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected reconcile(): void {
    const item = this.selected(); if (!item) return;
    this.loading.set(true); this.error.set(null);
    this.operations.reconcileInvestigation(item.id).subscribe({
      next: (detail) => {
        this.loading.set(false);
        this.selected.set(detail);
        this.loadEvidence(detail.id);
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected cancel(): void { this.mutate('cancel'); }
  protected resume(): void { this.mutate('resume'); }

  protected openTab(tab: string): void {
    this.activeTab.set(tab);
    const item = this.selected();
    if (item && tab === 'similar') this.operations.similar(item.id).subscribe({ next: (items) => this.similar.set(items) });
  }

  protected recordDecision(event: Event): void {
    event.preventDefault(); const item = this.selected(); if (!item) return;
    this.loading.set(true); this.error.set(null);
    this.operations.recordDecision(item.id, this.decisionVerdict(), this.decisionRationale()).subscribe({
      next: () => { this.loading.set(false); this.decisionRationale.set(''); this.select(item); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected friendly(value: string): string { return value.replaceAll('_', ' ').toLowerCase(); }

  private reload(): void { this.operations.investigations().subscribe({ next: (response) => this.items.set(response.items) }); }
  private loadEvidence(id: string): void { this.operations.evidence(id).subscribe({ next: (items) => this.evidence.set(items) }); }
  private mutate(action: 'cancel' | 'resume'): void {
    const item = this.selected(); if (!item) return; this.loading.set(true); this.error.set(null);
    const request = action === 'cancel' ? this.operations.cancelInvestigation(item.id) : this.operations.resumeInvestigation(item.id);
    request.subscribe({ next: (detail) => { this.loading.set(false); this.selected.set(detail); this.reload(); }, error: (response: HttpErrorResponse) => this.failed(response) });
  }
  private failed(response: HttpErrorResponse): void { this.loading.set(false); this.error.set(typeof response.error?.detail === 'string' ? response.error.detail : 'The investigation request failed.'); }
}

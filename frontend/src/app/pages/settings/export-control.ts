import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { AuthService } from '../../core/auth.service';
import { EligibleExportEvidence, ExportPolicy, ExportRequest } from '../../core/export.models';
import { ExportService } from '../../core/export.service';
import { TaxiiServer } from '../../core/taxii.models';
import { TaxiiService } from '../../core/taxii.service';

@Component({
  selector: 'app-export-control',
  imports: [DatePipe],
  templateUrl: './export-control.html',
  styleUrl: './export-control.scss',
})
export class ExportControl {
  protected readonly auth = inject(AuthService);
  private readonly exports = inject(ExportService);
  private readonly taxii = inject(TaxiiService);
  protected readonly servers = signal<TaxiiServer[]>([]);
  protected readonly policies = signal<ExportPolicy[]>([]);
  protected readonly requests = signal<ExportRequest[]>([]);
  protected readonly evidence = signal<EligibleExportEvidence[]>([]);
  protected readonly selectedEvidence = signal<Set<string>>(new Set());
  protected readonly policyId = signal('');
  protected readonly name = signal('');
  protected readonly collectionId = signal('');
  protected readonly markingText = signal('');
  protected readonly allowUnmarked = signal(false);
  protected readonly riskSummary = signal('');
  protected readonly rationale = signal('');
  protected readonly busy = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);

  constructor() {
    this.load();
  }

  protected writableCollections(): Array<{ id: string; label: string }> {
    return this.servers().flatMap((server) =>
      server.collections
        .filter((collection) => collection.can_write)
        .map((collection) => ({ id: collection.id, label: `${server.name} · ${collection.title}` })),
    );
  }

  protected update(
    field: 'name' | 'collectionId' | 'markingText' | 'riskSummary' | 'rationale',
    event: Event,
  ): void {
    const value = (event.target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement).value;
    if (field === 'name') this.name.set(value);
    if (field === 'collectionId') this.collectionId.set(value);
    if (field === 'markingText') this.markingText.set(value);
    if (field === 'riskSummary') this.riskSummary.set(value);
    if (field === 'rationale') this.rationale.set(value);
  }

  protected toggleUnmarked(event: Event): void {
    this.allowUnmarked.set((event.target as HTMLInputElement).checked);
  }

  protected createPolicy(event: Event): void {
    event.preventDefault();
    this.begin('create-policy');
    this.exports.createPolicy({
      name: this.name(),
      collection_id: this.collectionId(),
      allowed_marking_refs: this.markings(),
      allow_unmarked: this.allowUnmarked(),
      max_objects: 100,
    }).subscribe({
      next: (policy) => {
        this.message.set(`${policy.name} created disabled. Review and enable it explicitly.`);
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected togglePolicy(policy: ExportPolicy): void {
    this.begin(`policy:${policy.id}`);
    this.exports.configurePolicy(policy.id, {
      enabled: !policy.enabled,
      allowed_marking_refs: policy.allowed_marking_refs,
      allow_unmarked: policy.allow_unmarked,
      max_objects: policy.max_objects,
    }).subscribe({
      next: (updated) => {
        this.message.set(`${updated.name} ${updated.enabled ? 'enabled' : 'disabled'}.`);
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected selectPolicy(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.policyId.set(value);
    this.selectedEvidence.set(new Set());
    if (!value) {
      this.evidence.set([]);
      return;
    }
    this.exports.eligibleEvidence(value).subscribe({
      next: (items) => this.evidence.set(items),
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected toggleEvidence(item: EligibleExportEvidence): void {
    if (!item.eligible) return;
    this.selectedEvidence.update((selected) => {
      const updated = new Set(selected);
      if (updated.has(item.evidence_id)) updated.delete(item.evidence_id);
      else updated.add(item.evidence_id);
      return updated;
    });
  }

  protected requestExport(): void {
    this.begin('request');
    this.exports.request({
      policy_id: this.policyId(),
      evidence_ids: [...this.selectedEvidence()],
      risk_summary: this.riskSummary(),
    }).subscribe({
      next: (request) => {
        this.message.set(`Export ${request.bundle_id} frozen and awaiting independent approval.`);
        this.riskSummary.set('');
        this.selectedEvidence.set(new Set());
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected resolve(request: ExportRequest, status: 'APPROVED' | 'REJECTED'): void {
    this.begin(`resolve:${request.id}`);
    this.exports.resolve(request.id, status, this.rationale()).subscribe({
      next: (updated) => {
        this.message.set(`Export ${updated.status.toLowerCase()} after independent review.`);
        this.rationale.set('');
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected deliver(request: ExportRequest): void {
    this.begin(`deliver:${request.id}`);
    this.exports.deliver(request.id).subscribe({
      next: (updated) => {
        this.message.set(`Export delivery ${updated.status.toLowerCase()}.`);
        if (updated.error) this.error.set(updated.error);
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  private markings(): string[] {
    return this.markingText().split(/[\s,]+/).map((value) => value.trim()).filter(Boolean);
  }

  private begin(key: string): void {
    this.busy.set(key);
    this.message.set(null);
    this.error.set(null);
  }

  private load(): void {
    this.exports.policies().subscribe({ next: (items) => this.policies.set(items) });
    this.exports.requests().subscribe({ next: (items) => this.requests.set(items.slice(0, 10)) });
    if (this.auth.user()?.role === 'ADMIN') {
      this.taxii.servers().subscribe({ next: (items) => this.servers.set(items) });
    }
    this.busy.set(null);
  }

  private finishAndLoad(): void {
    this.load();
    if (this.policyId()) {
      this.exports.eligibleEvidence(this.policyId()).subscribe({
        next: (items) => this.evidence.set(items),
      });
    }
  }

  private failed(response: HttpErrorResponse): void {
    this.busy.set(null);
    this.error.set(
      typeof response.error?.detail === 'string' ? response.error.detail : 'Export operation failed.',
    );
  }
}

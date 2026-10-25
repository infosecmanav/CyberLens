import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { EnrichmentPolicy, EnrichmentRun } from '../../core/enrichment.models';
import { EnrichmentService } from '../../core/enrichment.service';

@Component({
  selector: 'app-enrichment-admin',
  imports: [DatePipe],
  templateUrl: './enrichment-admin.html',
  styleUrl: './enrichment-admin.scss',
})
export class EnrichmentAdmin {
  private readonly enrichment = inject(EnrichmentService);
  protected readonly policies = signal<EnrichmentPolicy[]>([]);
  protected readonly runs = signal<EnrichmentRun[]>([]);
  protected readonly name = signal('');
  protected readonly sourceId = signal('cisa-kev');
  protected readonly cadence = signal(60);
  protected readonly batchSize = signal(25);
  protected readonly busy = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);

  constructor() {
    this.load();
  }

  protected updateText(event: Event): void {
    this.name.set((event.target as HTMLInputElement).value);
  }

  protected updateNumber(field: 'cadence' | 'batchSize', event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    if (field === 'cadence') this.cadence.set(value);
    if (field === 'batchSize') this.batchSize.set(value);
  }

  protected updateSource(event: Event): void {
    this.sourceId.set((event.target as HTMLSelectElement).value);
  }

  protected create(event: Event): void {
    event.preventDefault();
    this.begin('create');
    this.enrichment.create({
      name: this.name(),
      entity_types: ['CVE'],
      source_ids: [this.sourceId()],
      max_entities_per_run: this.batchSize(),
      cadence_minutes: this.cadence(),
    }).subscribe({
      next: (policy) => {
        this.name.set('');
        this.message.set(`${policy.name} is scheduled for bounded enrichment.`);
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected toggle(policy: EnrichmentPolicy): void {
    this.begin(`toggle:${policy.id}`);
    this.enrichment.configure(policy.id, !policy.enabled, policy.cadence_minutes).subscribe({
      next: (updated) => {
        this.message.set(`${updated.name} ${updated.enabled ? 'resumed' : 'paused'}.`);
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected run(policy: EnrichmentPolicy): void {
    this.begin(`run:${policy.id}`);
    this.enrichment.run(policy.id).subscribe({
      next: (result) => {
        this.message.set(
          `${policy.name}: ${result.processed_entities} entities processed and ${result.new_observations} new observations recorded.`,
        );
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected outcomes(run: EnrichmentRun): string {
    const entries = Object.entries(run.source_outcomes);
    return entries.length
      ? entries.map(([outcome, count]) => `${outcome.toLowerCase().replaceAll('_', ' ')} ${count}`).join(' · ')
      : 'No candidates';
  }

  private begin(key: string): void {
    this.busy.set(key);
    this.message.set(null);
    this.error.set(null);
  }

  private load(): void {
    this.enrichment.policies().subscribe({
      next: (items) => this.policies.set(items),
      error: (response: HttpErrorResponse) => this.failed(response),
    });
    this.enrichment.runs().subscribe({
      next: (items) => this.runs.set(items.slice(0, 6)),
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  private finishAndLoad(): void {
    this.busy.set(null);
    this.load();
  }

  private failed(response: HttpErrorResponse): void {
    this.busy.set(null);
    this.error.set(
      typeof response.error?.detail === 'string'
        ? response.error.detail
        : 'Enrichment operation failed.',
    );
  }
}

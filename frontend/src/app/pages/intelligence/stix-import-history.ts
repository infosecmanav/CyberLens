import { DatePipe } from '@angular/common';
import { Component, effect, inject, input, signal } from '@angular/core';
import {
  ImportBatchDetail,
  ImportBatchSummary,
  StixImportFilterDefinition,
} from '../../core/intelligence.models';
import { IntelligenceService } from '../../core/intelligence.service';
import { StixEvidencePromotion } from './stix-evidence-promotion';

@Component({
  selector: 'app-stix-import-history',
  imports: [DatePipe, StixEvidencePromotion],
  templateUrl: './stix-import-history.html',
  styleUrl: './stix-import-history.scss',
})
export class StixImportHistory {
  private readonly intelligence = inject(IntelligenceService);
  readonly refreshKey = input<string | null>(null);
  protected readonly batches = signal<ImportBatchSummary[]>([]);
  protected readonly selected = signal<ImportBatchDetail | null>(null);
  protected readonly available = signal(false);
  protected readonly loading = signal(false);
  protected readonly detailLoading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly promotionFilter = signal<'ALL' | 'PROMOTED' | 'UNPROMOTED'>('ALL');

  constructor() {
    effect(() => {
      this.refreshKey();
      this.load();
    });
  }

  protected inspect(batch: ImportBatchSummary): void {
    this.detailLoading.set(true);
    this.error.set(null);
    this.intelligence.importDetail(batch.id).subscribe({
      next: (detail) => {
        this.selected.set(detail);
        this.detailLoading.set(false);
      },
      error: () => {
        this.error.set('The persisted import report could not be loaded.');
        this.detailLoading.set(false);
      },
    });
  }

  protected close(): void { this.selected.set(null); }

  protected friendly(value: string): string {
    return value.replaceAll('_', ' ').toLowerCase();
  }

  protected filterLabels(filter: StixImportFilterDefinition): string[] {
    const labels: string[] = [];
    if (filter.entity_types?.length) labels.push(`Types: ${filter.entity_types.join(', ')}`);
    if (filter.minimum_confidence !== undefined) {
      labels.push(`Confidence ≥ ${filter.minimum_confidence}`);
    }
    if (filter.valid_from_start) labels.push(`From ${filter.valid_from_start}`);
    if (filter.valid_from_end) labels.push(`Through ${filter.valid_from_end}`);
    if (filter.required_marking_refs?.length) {
      labels.push(`${filter.required_marking_refs.length} required marking(s)`);
    }
    return labels;
  }

  protected promotionComplete(): void {
    const current = this.selected();
    if (current) this.inspect(current);
    this.load();
  }

  protected setPromotionFilter(value: 'ALL' | 'PROMOTED' | 'UNPROMOTED'): void {
    this.promotionFilter.set(value);
    this.selected.set(null);
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    const filter = this.promotionFilter();
    const hasPromotions = filter === 'ALL' ? undefined : filter === 'PROMOTED';
    this.intelligence.imports(undefined, hasPromotions).subscribe({
      next: (response) => {
        this.batches.set(response.items);
        this.available.set(true);
        this.loading.set(false);
      },
      error: () => {
        this.batches.set([]);
        this.available.set(false);
        this.loading.set(false);
      },
    });
  }
}

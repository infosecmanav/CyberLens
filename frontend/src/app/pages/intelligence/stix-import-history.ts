import { DatePipe } from '@angular/common';
import { Component, effect, inject, input, signal } from '@angular/core';
import { ImportBatchDetail, ImportBatchSummary } from '../../core/intelligence.models';
import { IntelligenceService } from '../../core/intelligence.service';

@Component({
  selector: 'app-stix-import-history',
  imports: [DatePipe],
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

  private load(): void {
    this.loading.set(true);
    this.intelligence.imports().subscribe({
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

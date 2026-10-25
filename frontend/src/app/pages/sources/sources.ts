import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { AuthService } from '../../core/auth.service';
import { SourceDetail, SourceSummary } from '../../core/source.models';
import { SourcesService } from '../../core/sources.service';

@Component({ selector: 'app-sources', imports: [DatePipe], templateUrl: './sources.html', styleUrl: './sources.scss' })
export class Sources {
  protected readonly auth = inject(AuthService);
  private readonly sourceService = inject(SourcesService);
  protected readonly sources = signal<SourceSummary[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal(false);
  protected readonly query = signal('');
  protected readonly selectedCategory = signal('ALL');
  protected readonly selected = signal<SourceDetail | null>(null);
  protected readonly testType = signal('DOMAIN');
  protected readonly testValue = signal('example.test');
  protected readonly testing = signal(false);
  protected readonly testResult = signal<string | null>(null);
  protected readonly categories = computed(() => ['ALL', ...Array.from(new Set(this.sources().map((source) => source.category))).sort()]);
  protected readonly filteredSources = computed(() => {
    const query = this.query().toLowerCase().trim();
    return this.sources().filter((source) => {
      const matchesCategory = this.selectedCategory() === 'ALL' || source.category === this.selectedCategory();
      const matchesQuery = !query || source.name.toLowerCase().includes(query) || source.source_id.toLowerCase().includes(query);
      return matchesCategory && matchesQuery;
    });
  });
  constructor() {
    this.sourceService.list().subscribe({
      next: (response) => { this.sources.set(response.items); this.loading.set(false); },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }
  protected updateQuery(event: Event): void { this.query.set((event.target as HTMLInputElement).value); }
  protected updateCategory(event: Event): void { this.selectedCategory.set((event.target as HTMLSelectElement).value); }
  protected inspect(source: SourceSummary): void {
    this.sourceService.detail(source.source_id).subscribe({
      next: (detail) => {
        this.selected.set(detail);
        this.testType.set(detail.supported_entity_types[0] || 'DOMAIN');
        this.testResult.set(null);
      },
    });
  }
  protected closeDetail(): void { this.selected.set(null); this.testResult.set(null); }
  protected updateTest(field: 'type' | 'value', event: Event): void {
    const value = (event.target as HTMLInputElement | HTMLSelectElement).value;
    if (field === 'type') this.testType.set(value);
    if (field === 'value') this.testValue.set(value);
  }
  protected testSource(source: SourceDetail): void {
    this.testing.set(true);
    this.testResult.set(null);
    this.sourceService.test(source.source_id, this.testType(), this.testValue()).subscribe({
      next: (result) => {
        this.testing.set(false);
        const state = this.friendlyStatus(result.outcome || result.health_status);
        this.testResult.set(`${state}${result.message ? ` · ${result.message}` : ''}`);
        this.sourceService.detail(source.source_id).subscribe({
          next: (detail) => this.selected.set(detail),
        });
      },
      error: (response) => {
        this.testing.set(false);
        this.testResult.set(
          typeof response.error?.detail === 'string'
            ? response.error.detail
            : 'Source test failed.',
        );
      },
    });
  }
  protected friendlyStatus(status: string): string { return status.replaceAll('_', ' ').toLowerCase(); }
}

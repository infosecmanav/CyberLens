import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { SourceDetail, SourceSummary } from '../../core/source.models';
import { SourcesService } from '../../core/sources.service';

@Component({ selector: 'app-sources', imports: [DatePipe], templateUrl: './sources.html', styleUrl: './sources.scss' })
export class Sources {
  private readonly sourceService = inject(SourcesService);
  protected readonly sources = signal<SourceSummary[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal(false);
  protected readonly query = signal('');
  protected readonly selectedCategory = signal('ALL');
  protected readonly selected = signal<SourceDetail | null>(null);
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
  protected inspect(source: SourceSummary): void { this.sourceService.detail(source.source_id).subscribe({ next: (detail) => this.selected.set(detail) }); }
  protected closeDetail(): void { this.selected.set(null); }
  protected friendlyStatus(status: string): string { return status.replaceAll('_', ' ').toLowerCase(); }
}

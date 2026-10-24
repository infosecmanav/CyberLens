import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SourceSummary } from '../../core/source.models';
import { SourcesService } from '../../core/sources.service';
import { OperationsMetrics } from '../../core/operations.models';
import { OperationsService } from '../../core/operations.service';

@Component({ selector: 'app-dashboard', imports: [RouterLink], templateUrl: './dashboard.html', styleUrl: './dashboard.scss' })
export class Dashboard {
  private readonly sourceService = inject(SourcesService);
  private readonly operations = inject(OperationsService);
  protected readonly sources = signal<SourceSummary[]>([]);
  protected readonly metrics = signal<OperationsMetrics | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal(false);
  protected readonly configured = computed(() => this.sources().filter((source) => source.implementation_status === 'IMPLEMENTED_AND_TESTED').length);
  protected readonly awaitingReview = computed(() => this.sources().length - this.configured());
  constructor() {
    this.sourceService.list().subscribe({
      next: (response) => { this.sources.set(response.items); this.loading.set(false); },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
    this.operations.metrics().subscribe({ next: (metrics) => this.metrics.set(metrics) });
  }
}

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
  protected readonly metricsError = signal(false);
  protected readonly loading = signal(true);
  protected readonly error = signal(false);
  protected readonly configured = computed(() => this.sources().filter((source) => source.implementation_status === 'IMPLEMENTED_AND_TESTED').length);
  protected readonly awaitingReview = computed(() => this.sources().length - this.configured());
  protected readonly sourceHealth = computed(() => this.percent(this.metrics()?.sources_healthy ?? this.configured(), this.metrics()?.source_total ?? this.sources().length));
  protected readonly investigationSettled = computed(() => this.percent((this.metrics()?.investigations_total ?? 0) - (this.metrics()?.investigations_running ?? 0), this.metrics()?.investigations_total ?? 0));
  protected readonly detectionValidation = computed(() => this.percent(this.metrics()?.validated_detections ?? 0, this.metrics()?.detection_candidates ?? 0));
  constructor() {
    this.sourceService.list().subscribe({
      next: (response) => { this.sources.set(response.items); this.loading.set(false); },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
    this.operations.metrics().subscribe({
      next: (metrics) => this.metrics.set(metrics),
      error: () => this.metricsError.set(true),
    });
  }

  private percent(value: number, total: number): number {
    return total > 0 ? Math.max(0, Math.min(100, Math.round((value / total) * 100))) : 0;
  }
}

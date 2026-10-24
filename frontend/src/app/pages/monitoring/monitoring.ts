import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { IntelligenceEntity } from '../../core/intelligence.models';
import { IntelligenceChange, MonitoringObjective } from '../../core/operations.models';
import { OperationsService } from '../../core/operations.service';

@Component({ selector: 'app-monitoring', imports: [DatePipe, RouterLink], templateUrl: './monitoring.html', styleUrl: './monitoring.scss' })
export class Monitoring {
  protected readonly auth = inject(AuthService);
  private readonly operations = inject(OperationsService);
  protected readonly objectives = signal<MonitoringObjective[]>([]);
  protected readonly changes = signal<IntelligenceChange[]>([]);
  protected readonly entities = signal<IntelligenceEntity[]>([]);
  protected readonly name = signal('');
  protected readonly objective = signal('');
  protected readonly entityId = signal('');
  protected readonly cadence = signal(1440);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);

  constructor() { this.reload(); this.operations.entities().subscribe({ next: (response) => this.entities.set(response.items) }); }

  protected update(field: 'name' | 'objective' | 'entity' | 'cadence', event: Event): void {
    const value = (event.target as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement).value;
    if (field === 'name') this.name.set(value); if (field === 'objective') this.objective.set(value);
    if (field === 'entity') this.entityId.set(value); if (field === 'cadence') this.cadence.set(Number(value));
  }

  protected create(event: Event): void {
    event.preventDefault(); this.begin();
    this.operations.createObjective({ name: this.name(), objective: this.objective(), cadence_minutes: this.cadence(), ...(this.entityId() ? { entity_id: this.entityId() } : {}) }).subscribe({
      next: () => { this.loading.set(false); this.message.set('Monitoring objective scheduled.'); this.name.set(''); this.objective.set(''); this.reload(); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected run(item: MonitoringObjective): void {
    this.begin(); this.operations.runObjective(item.id).subscribe({
      next: (run) => { this.loading.set(false); this.message.set(`Monitoring run ${this.friendly(run.status)}. Duplicates are retained without becoming actionable.`); this.reload(); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected acknowledge(item: IntelligenceChange): void {
    this.begin(); this.operations.acknowledgeChange(item.id).subscribe({ next: () => { this.loading.set(false); this.message.set('Change acknowledged.'); this.reload(); }, error: (response: HttpErrorResponse) => this.failed(response) });
  }

  protected friendly(value: string): string { return value.replaceAll('_', ' ').toLowerCase(); }
  protected entityLabel(id: string | null): string { return this.entities().find((item) => item.id === id)?.value || 'Workspace-wide'; }
  private begin(): void { this.loading.set(true); this.error.set(null); this.message.set(null); }
  private reload(): void {
    this.operations.objectives().subscribe({ next: (items) => this.objectives.set(items), error: () => this.error.set('Monitoring objectives could not be loaded.') });
    this.operations.changes().subscribe({ next: (items) => this.changes.set(items) });
  }
  private failed(response: HttpErrorResponse): void { this.loading.set(false); this.error.set(typeof response.error?.detail === 'string' ? response.error.detail : 'The monitoring request failed.'); }
}

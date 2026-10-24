import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { Playbook, PlaybookExecution } from '../../core/operations.models';
import { OperationsService } from '../../core/operations.service';

@Component({ selector: 'app-playbooks', imports: [RouterLink], templateUrl: './playbooks.html', styleUrl: './playbooks.scss' })
export class Playbooks {
  protected readonly auth = inject(AuthService);
  private readonly operations = inject(OperationsService);
  protected readonly items = signal<Playbook[]>([]);
  protected readonly execution = signal<PlaybookExecution | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() { this.operations.playbooks().subscribe({ next: (items) => this.items.set(items), error: () => this.error.set('Playbooks could not be loaded.') }); }

  protected execute(item: Playbook): void {
    this.loading.set(true); this.error.set(null); this.execution.set(null);
    this.operations.executePlaybook(item.id).subscribe({
      next: (execution) => { this.loading.set(false); this.execution.set(execution); },
      error: (response: HttpErrorResponse) => { this.loading.set(false); this.error.set(typeof response.error?.detail === 'string' ? response.error.detail : 'The playbook run failed.'); },
    });
  }

  protected stepName(step: Record<string, unknown>): string { return String(step['name'] || step['action'] || 'Controlled step'); }
  protected eventName(event: Record<string, unknown>): string { return String(event['name'] || `Step ${Number(event['step']) + 1}`); }
}

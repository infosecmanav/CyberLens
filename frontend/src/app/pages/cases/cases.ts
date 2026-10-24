import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { ApprovalRequest, CaseRecord, CaseTask } from '../../core/operations.models';
import { OperationsService } from '../../core/operations.service';

@Component({ selector: 'app-cases', imports: [RouterLink], templateUrl: './cases.html', styleUrl: './cases.scss' })
export class Cases {
  protected readonly auth = inject(AuthService);
  private readonly operations = inject(OperationsService);
  protected readonly items = signal<CaseRecord[]>([]);
  protected readonly selected = signal<CaseRecord | null>(null);
  protected readonly tasks = signal<CaseTask[]>([]);
  protected readonly approval = signal<ApprovalRequest | null>(null);
  protected readonly title = signal('');
  protected readonly summary = signal('');
  protected readonly priority = signal('MEDIUM');
  protected readonly taskTitle = signal('');
  protected readonly taskDescription = signal('');
  protected readonly actionType = signal('INTERNAL_TASK');
  protected readonly highImpact = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);
  protected readonly loading = signal(false);

  constructor() { this.reload(); }

  protected update(field: 'title' | 'summary' | 'priority' | 'taskTitle' | 'taskDescription' | 'actionType', event: Event): void {
    const value = (event.target as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement).value;
    if (field === 'title') this.title.set(value); if (field === 'summary') this.summary.set(value);
    if (field === 'priority') this.priority.set(value); if (field === 'taskTitle') this.taskTitle.set(value);
    if (field === 'taskDescription') this.taskDescription.set(value); if (field === 'actionType') this.actionType.set(value);
  }

  protected toggleImpact(event: Event): void { this.highImpact.set((event.target as HTMLInputElement).checked); }

  protected createCase(event: Event): void {
    event.preventDefault(); this.begin();
    this.operations.createCase({ title: this.title(), summary: this.summary(), priority: this.priority() }).subscribe({
      next: (item) => { this.loading.set(false); this.title.set(''); this.summary.set(''); this.select(item); this.reload(); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected select(item: CaseRecord): void { this.selected.set(item); this.approval.set(null); this.loadTasks(item.id); }

  protected addTask(event: Event): void {
    event.preventDefault(); const item = this.selected(); if (!item) return; this.begin();
    this.operations.createTask(item.id, { title: this.taskTitle(), description: this.taskDescription(), action_type: this.actionType(), high_impact: this.highImpact() }).subscribe({
      next: () => { this.loading.set(false); this.taskTitle.set(''); this.taskDescription.set(''); this.highImpact.set(false); this.loadTasks(item.id); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected execute(task: CaseTask): void {
    this.begin(); this.operations.executeTask(task.id).subscribe({
      next: () => { this.loading.set(false); this.message.set('Task completed as a dry run; no external action was performed.'); this.loadSelectedTasks(); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected requestApproval(task: CaseTask): void {
    this.begin(); this.operations.requestApproval(task.id, `Review ${task.action_type} because it may affect systems or users.`).subscribe({
      next: (approval) => { this.loading.set(false); this.approval.set(approval); this.message.set('Approval request recorded.'); this.loadSelectedTasks(); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected resolve(status: 'APPROVED' | 'REJECTED'): void {
    const approval = this.approval(); if (!approval) return; this.begin();
    this.operations.resolveApproval(approval.id, status, `${status === 'APPROVED' ? 'Approved' : 'Rejected'} after analyst review; execution remains dry-run only.`).subscribe({
      next: (resolved) => { this.loading.set(false); this.approval.set(resolved); this.message.set(`Request ${status.toLowerCase()}.`); this.loadSelectedTasks(); },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected friendly(value: string): string { return value.replaceAll('_', ' ').toLowerCase(); }
  private begin(): void { this.loading.set(true); this.error.set(null); this.message.set(null); }
  private reload(): void { this.operations.cases().subscribe({ next: (items) => this.items.set(items), error: () => this.error.set('Cases could not be loaded.') }); }
  private loadSelectedTasks(): void { const item = this.selected(); if (item) this.loadTasks(item.id); }
  private loadTasks(id: string): void { this.operations.tasks(id).subscribe({ next: (tasks) => this.tasks.set(tasks) }); }
  private failed(response: HttpErrorResponse): void { this.loading.set(false); this.error.set(typeof response.error?.detail === 'string' ? response.error.detail : 'The case request failed.'); }
}

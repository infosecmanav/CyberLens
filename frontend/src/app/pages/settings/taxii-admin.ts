import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { TaxiiCollection, TaxiiServer } from '../../core/taxii.models';
import { TaxiiService } from '../../core/taxii.service';

@Component({
  selector: 'app-taxii-admin',
  imports: [DatePipe],
  templateUrl: './taxii-admin.html',
  styleUrl: './taxii-admin.scss',
})
export class TaxiiAdmin {
  private readonly taxii = inject(TaxiiService);
  protected readonly servers = signal<TaxiiServer[]>([]);
  protected readonly name = signal('');
  protected readonly discoveryUrl = signal('');
  protected readonly environmentVariable = signal('');
  protected readonly busy = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);

  constructor() {
    this.load();
  }

  protected update(
    field: 'name' | 'discoveryUrl' | 'environmentVariable',
    event: Event,
  ): void {
    const value = (event.target as HTMLInputElement).value;
    if (field === 'name') this.name.set(value);
    if (field === 'discoveryUrl') this.discoveryUrl.set(value);
    if (field === 'environmentVariable') this.environmentVariable.set(value);
  }

  protected create(event: Event): void {
    event.preventDefault();
    this.begin('create');
    this.taxii.create({
      name: this.name(),
      discovery_url: this.discoveryUrl(),
      auth_environment_variable: this.environmentVariable() || null,
    }).subscribe({
      next: (server) => {
        this.name.set('');
        this.discoveryUrl.set('');
        this.environmentVariable.set('');
        this.message.set(`${server.name} saved. Run discovery to review its collections.`);
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected discover(server: TaxiiServer): void {
    this.begin(`discover:${server.id}`);
    this.taxii.discover(server.id).subscribe({
      next: (updated) => {
        this.replaceServer(updated);
        this.busy.set(null);
        this.message.set(`Discovered ${updated.collections.length} collections from ${updated.name}.`);
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected toggle(collection: TaxiiCollection): void {
    this.begin(`collection:${collection.id}`);
    this.taxii.configureCollection(
      collection.id,
      !collection.selected,
      collection.poll_interval_minutes,
    ).subscribe({
      next: () => {
        this.message.set(
          `${collection.title} ${collection.selected ? 'paused' : 'scheduled for collection'}.`,
        );
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected run(collection: TaxiiCollection): void {
    this.begin(`run:${collection.id}`);
    this.taxii.run(collection.id).subscribe({
      next: (run) => {
        this.message.set(
          `${collection.title}: ${run.accepted_objects}/${run.received_objects} objects accepted (${run.status.toLowerCase().replaceAll('_', ' ')}).`,
        );
        if (run.error) this.error.set(run.error);
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  private begin(key: string): void {
    this.busy.set(key);
    this.error.set(null);
    this.message.set(null);
  }

  private load(): void {
    this.taxii.servers().subscribe({
      next: (servers) => this.servers.set(servers),
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  private finishAndLoad(): void {
    this.busy.set(null);
    this.load();
  }

  private replaceServer(updated: TaxiiServer): void {
    this.servers.update((servers) =>
      servers.map((server) => server.id === updated.id ? updated : server),
    );
  }

  private failed(response: HttpErrorResponse): void {
    this.busy.set(null);
    this.error.set(
      typeof response.error?.detail === 'string' ? response.error.detail : 'TAXII operation failed.',
    );
  }
}

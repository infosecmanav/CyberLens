import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FeedRun, FeedSubscription } from '../../core/feed.models';
import { FeedService } from '../../core/feed.service';

@Component({
  selector: 'app-feed-admin',
  imports: [DatePipe],
  templateUrl: './feed-admin.html',
  styleUrl: './feed-admin.scss',
})
export class FeedAdmin {
  private readonly feeds = inject(FeedService);
  protected readonly subscriptions = signal<FeedSubscription[]>([]);
  protected readonly runs = signal<FeedRun[]>([]);
  protected readonly name = signal('Official CISA KEV');
  protected readonly cadence = signal(60);
  protected readonly maxRecords = signal(1000);
  protected readonly busy = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);

  constructor() {
    this.load();
  }

  protected updateName(event: Event): void {
    this.name.set((event.target as HTMLInputElement).value);
  }

  protected updateNumber(field: 'cadence' | 'maxRecords', event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    if (field === 'cadence') this.cadence.set(value);
    if (field === 'maxRecords') this.maxRecords.set(value);
  }

  protected create(event: Event): void {
    event.preventDefault();
    this.begin('create');
    this.feeds.create({
      name: this.name(),
      source_id: 'cisa-kev',
      cadence_minutes: this.cadence(),
      max_records: this.maxRecords(),
    }).subscribe({
      next: (subscription) => {
        this.message.set(`${subscription.name} is scheduled with a hard record budget.`);
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected toggle(subscription: FeedSubscription): void {
    this.begin(`toggle:${subscription.id}`);
    this.feeds.configure(
      subscription.id,
      !subscription.enabled,
      subscription.cadence_minutes,
      subscription.max_records,
    ).subscribe({
      next: (updated) => {
        this.message.set(`${updated.name} ${updated.enabled ? 'resumed' : 'paused'}.`);
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  protected run(subscription: FeedSubscription): void {
    this.begin(`run:${subscription.id}`);
    this.feeds.run(subscription.id).subscribe({
      next: (result) => {
        this.message.set(
          `${subscription.name}: ${result.new_observations} new and ${result.deduplicated_observations} deduplicated observations.`,
        );
        this.finishAndLoad();
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  private begin(key: string): void {
    this.busy.set(key);
    this.message.set(null);
    this.error.set(null);
  }

  private load(): void {
    this.feeds.subscriptions().subscribe({
      next: (items) => this.subscriptions.set(items),
      error: (response: HttpErrorResponse) => this.failed(response),
    });
    this.feeds.runs().subscribe({
      next: (items) => this.runs.set(items.slice(0, 6)),
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  private finishAndLoad(): void {
    this.busy.set(null);
    this.load();
  }

  private failed(response: HttpErrorResponse): void {
    this.busy.set(null);
    this.error.set(
      typeof response.error?.detail === 'string'
        ? response.error.detail
        : 'Feed operation failed.',
    );
  }
}

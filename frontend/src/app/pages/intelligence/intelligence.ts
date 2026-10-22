import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import {
  IntelligenceEntity,
  IntelligenceObservation,
  LookupResponse,
} from '../../core/intelligence.models';
import { IntelligenceService } from '../../core/intelligence.service';

@Component({
  selector: 'app-intelligence',
  imports: [DatePipe, RouterLink],
  templateUrl: './intelligence.html',
  styleUrl: './intelligence.scss',
})
export class Intelligence {
  private readonly intelligence = inject(IntelligenceService);
  protected readonly value = signal('');
  protected readonly entityType = signal('AUTO');
  protected readonly includeDemo = signal(false);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly result = signal<LookupResponse | null>(null);
  protected readonly observations = signal<IntelligenceObservation[]>([]);
  protected readonly recent = signal<IntelligenceEntity[]>([]);
  protected readonly entityTypes = [
    'AUTO', 'IPV4', 'IPV6', 'DOMAIN', 'URL', 'MD5', 'SHA1', 'SHA256', 'EMAIL',
    'CVE', 'ASN', 'CERTIFICATE', 'NAMESERVER', 'NETWORK_RANGE', 'PRODUCT',
    'MALWARE_FAMILY', 'CAMPAIGN', 'THREAT_ACTOR', 'ATTACK_TECHNIQUE',
  ];

  constructor() {
    this.loadRecent();
  }

  protected submit(event: Event): void {
    event.preventDefault();
    const candidate = this.value().trim();
    if (!candidate || this.loading()) return;
    this.loading.set(true);
    this.error.set(null);
    this.result.set(null);
    this.observations.set([]);
    const type = this.entityType();
    this.intelligence.lookup({
      value: candidate,
      ...(type === 'AUTO' ? {} : { entity_type: type }),
      include_demo: this.includeDemo(),
    }).subscribe({
      next: (response) => {
        this.result.set(response);
        this.intelligence.observations(response.entity.id).subscribe({
          next: (items) => {
            this.observations.set(items);
            this.loading.set(false);
            this.loadRecent();
          },
          error: () => {
            this.error.set('The lookup completed, but persisted observations could not be loaded.');
            this.loading.set(false);
          },
        });
      },
      error: (response: HttpErrorResponse) => {
        this.error.set(this.errorMessage(response));
        this.loading.set(false);
      },
    });
  }

  protected updateValue(event: Event): void {
    this.value.set((event.target as HTMLInputElement).value);
  }

  protected updateType(event: Event): void {
    this.entityType.set((event.target as HTMLSelectElement).value);
  }

  protected updateDemo(event: Event): void {
    this.includeDemo.set((event.target as HTMLInputElement).checked);
  }

  protected useRecent(entity: IntelligenceEntity): void {
    this.value.set(entity.normalized_value);
    this.entityType.set(entity.entity_type);
  }

  protected friendly(value: string): string {
    return value.replaceAll('_', ' ').toLowerCase();
  }

  protected isHealthy(outcome: string): boolean {
    return outcome === 'SUCCESS' || outcome === 'NO_RESULT';
  }

  private loadRecent(): void {
    this.intelligence.recent().subscribe({ next: (response) => this.recent.set(response.items) });
  }

  private errorMessage(response: HttpErrorResponse): string {
    const detail = response.error?.detail;
    if (typeof detail === 'string') return detail;
    return 'The intelligence API could not complete this lookup.';
  }
}

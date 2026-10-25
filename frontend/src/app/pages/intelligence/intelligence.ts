import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import {
  IntelligenceEntity,
  IntelligenceObservation,
  LookupResponse,
  StixImportResponse,
} from '../../core/intelligence.models';
import { IntelligenceService } from '../../core/intelligence.service';
import { StixImportHistory } from './stix-import-history';

@Component({
  selector: 'app-intelligence',
  imports: [DatePipe, RouterLink, StixImportHistory],
  templateUrl: './intelligence.html',
  styleUrl: './intelligence.scss',
})
export class Intelligence {
  private readonly maxStixFileBytes = 2 * 1024 * 1024;
  private readonly intelligence = inject(IntelligenceService);
  protected readonly value = signal('');
  protected readonly entityType = signal('AUTO');
  protected readonly includeDemo = signal(false);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly result = signal<LookupResponse | null>(null);
  protected readonly observations = signal<IntelligenceObservation[]>([]);
  protected readonly recent = signal<IntelligenceEntity[]>([]);
  protected readonly stixBundle = signal<Record<string, unknown> | null>(null);
  protected readonly stixFileName = signal<string | null>(null);
  protected readonly stixSourceReference = signal('');
  protected readonly importLoading = signal(false);
  protected readonly importError = signal<string | null>(null);
  protected readonly importResult = signal<StixImportResponse | null>(null);
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

  protected async selectStixFile(event: Event): Promise<void> {
    const file = (event.target as HTMLInputElement).files?.[0];
    this.stixBundle.set(null);
    this.stixFileName.set(null);
    this.importResult.set(null);
    this.importError.set(null);
    if (!file) return;
    if (file.size > this.maxStixFileBytes) {
      this.importError.set('The STIX bundle exceeds the 2 MiB import limit.');
      return;
    }
    try {
      const parsed: unknown = JSON.parse(await file.text());
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        throw new Error('Bundle root is not an object');
      }
      this.stixBundle.set(parsed as Record<string, unknown>);
      this.stixFileName.set(file.name);
    } catch {
      this.importError.set('Choose a valid JSON file containing a STIX 2.1 bundle.');
    }
  }

  protected updateStixSourceReference(event: Event): void {
    this.stixSourceReference.set((event.target as HTMLInputElement).value);
  }

  protected submitStixImport(event: Event): void {
    event.preventDefault();
    const bundle = this.stixBundle();
    if (!bundle || this.importLoading()) return;
    const sourceReference = this.stixSourceReference().trim();
    this.importLoading.set(true);
    this.importError.set(null);
    this.importResult.set(null);
    this.intelligence.importStix({
      bundle,
      ...(sourceReference ? { source_reference: sourceReference } : {}),
    }).subscribe({
      next: (response) => {
        this.importResult.set(response);
        this.importLoading.set(false);
        this.loadRecent();
      },
      error: (response: HttpErrorResponse) => {
        this.importError.set(this.errorMessage(response));
        this.importLoading.set(false);
      },
    });
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

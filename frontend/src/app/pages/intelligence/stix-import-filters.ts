import { Component, computed, output, signal } from '@angular/core';
import { StixImportFilterDefinition } from '../../core/intelligence.models';

@Component({
  selector: 'app-stix-import-filters',
  templateUrl: './stix-import-filters.html',
  styleUrl: './stix-import-filters.scss',
})
export class StixImportFilters {
  readonly filtersChange = output<StixImportFilterDefinition>();
  protected readonly entityTypes = [
    'IPV4', 'IPV6', 'DOMAIN', 'URL', 'EMAIL', 'MD5', 'SHA1', 'SHA256',
  ];
  protected readonly selectedTypes = signal<string[]>([]);
  protected readonly minimumConfidence = signal('');
  protected readonly validFromStart = signal('');
  protected readonly validFromEnd = signal('');
  protected readonly requiredMarkings = signal('');
  protected readonly activeCount = computed(() => [
    this.selectedTypes().length > 0,
    this.minimumConfidence().trim() !== '',
    this.validFromStart() !== '' || this.validFromEnd() !== '',
    this.requiredMarkings().trim() !== '',
  ].filter(Boolean).length);

  protected friendly(value: string): string {
    return value.replaceAll('_', ' ').toLowerCase();
  }

  protected toggleType(event: Event, entityType: string): void {
    const selected = (event.target as HTMLInputElement).checked;
    this.selectedTypes.update((current) => selected
      ? [...current, entityType]
      : current.filter((value) => value !== entityType));
    this.emitDefinition();
  }

  protected updateMinimumConfidence(event: Event): void {
    this.minimumConfidence.set((event.target as HTMLInputElement).value);
    this.emitDefinition();
  }

  protected updateValidFromStart(event: Event): void {
    this.validFromStart.set((event.target as HTMLInputElement).value);
    this.emitDefinition();
  }

  protected updateValidFromEnd(event: Event): void {
    this.validFromEnd.set((event.target as HTMLInputElement).value);
    this.emitDefinition();
  }

  protected updateRequiredMarkings(event: Event): void {
    this.requiredMarkings.set((event.target as HTMLInputElement).value);
    this.emitDefinition();
  }

  protected clear(): void {
    this.selectedTypes.set([]);
    this.minimumConfidence.set('');
    this.validFromStart.set('');
    this.validFromEnd.set('');
    this.requiredMarkings.set('');
    this.emitDefinition();
  }

  private emitDefinition(): void {
    const definition: StixImportFilterDefinition = {};
    const entityTypes = this.selectedTypes();
    const confidence = this.minimumConfidence().trim();
    const validFromStart = this.validFromStart();
    const validFromEnd = this.validFromEnd();
    const markingRefs = this.requiredMarkings()
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);
    if (entityTypes.length) definition.entity_types = entityTypes;
    if (confidence !== '') definition.minimum_confidence = Number(confidence);
    if (validFromStart) definition.valid_from_start = new Date(validFromStart).toISOString();
    if (validFromEnd) definition.valid_from_end = new Date(validFromEnd).toISOString();
    if (markingRefs.length) definition.required_marking_refs = markingRefs;
    this.filtersChange.emit(definition);
  }
}

import { Component, computed, inject, input, output, signal } from '@angular/core';
import { EvidencePromotionPayload } from '../../core/intelligence.models';
import { IntelligenceService } from '../../core/intelligence.service';

@Component({
  selector: 'app-stix-evidence-promotion',
  templateUrl: './stix-evidence-promotion.html',
  styleUrl: './stix-evidence-promotion.scss',
})
export class StixEvidencePromotion {
  private readonly intelligence = inject(IntelligenceService);
  readonly importId = input.required<string>();
  readonly outcomeId = input.required<string>();
  readonly promoted = output<void>();
  protected readonly open = signal(false);
  protected readonly polarity = signal<EvidencePromotionPayload['polarity']>('CONTEXTUAL');
  protected readonly assessmentDimension = signal<
    EvidencePromotionPayload['assessment_dimension']
  >('GENERAL_CONTEXT');
  protected readonly claim = signal('');
  protected readonly uncertaintyNotes = signal('');
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly canSubmit = computed(() => (
    this.claim().trim().length >= 10
    && this.uncertaintyNotes().trim().length >= 10
    && !this.loading()
  ));

  protected begin(): void {
    this.open.set(true);
    this.error.set(null);
  }

  protected cancel(): void {
    this.open.set(false);
    this.error.set(null);
  }

  protected updatePolarity(event: Event): void {
    this.polarity.set((event.target as HTMLSelectElement).value as EvidencePromotionPayload['polarity']);
  }

  protected updateDimension(event: Event): void {
    this.assessmentDimension.set(
      (event.target as HTMLSelectElement).value as EvidencePromotionPayload['assessment_dimension'],
    );
  }

  protected updateClaim(event: Event): void {
    this.claim.set((event.target as HTMLTextAreaElement).value);
  }

  protected updateUncertainty(event: Event): void {
    this.uncertaintyNotes.set((event.target as HTMLTextAreaElement).value);
  }

  protected submit(event: Event): void {
    event.preventDefault();
    if (!this.canSubmit()) return;
    this.loading.set(true);
    this.error.set(null);
    this.intelligence.promoteImportObject(this.importId(), this.outcomeId(), {
      polarity: this.polarity(),
      assessment_dimension: this.assessmentDimension(),
      claim: this.claim().trim(),
      uncertainty_notes: this.uncertaintyNotes().trim(),
    }).subscribe({
      next: () => {
        this.loading.set(false);
        this.open.set(false);
        this.promoted.emit();
      },
      error: () => {
        this.error.set('Evidence promotion could not be recorded. Refresh the import report.');
        this.loading.set(false);
      },
    });
  }
}

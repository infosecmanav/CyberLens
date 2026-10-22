import { Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

@Component({ selector: 'app-placeholder', templateUrl: './placeholder.html', styleUrl: './placeholder.scss' })
export class Placeholder {
  private readonly route = inject(ActivatedRoute);
  protected readonly title = this.route.snapshot.data['title'] as string;
  protected readonly phase = this.route.snapshot.data['phase'] as string;
  protected readonly description = this.route.snapshot.data['description'] as string;
}

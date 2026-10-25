import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { AuthService } from '../../core/auth.service';
import { AuditEvent } from '../../core/operations.models';
import { OperationsService } from '../../core/operations.service';
import { TaxiiAdmin } from './taxii-admin';
import { EnrichmentAdmin } from './enrichment-admin';

@Component({ selector: 'app-settings', imports: [DatePipe, EnrichmentAdmin, TaxiiAdmin], templateUrl: './settings.html', styleUrl: './settings.scss' })
export class Settings {
  protected readonly auth = inject(AuthService);
  private readonly operations = inject(OperationsService);
  protected readonly mode = signal<'login' | 'register'>('login');
  protected readonly email = signal('');
  protected readonly displayName = signal('');
  protected readonly password = signal('');
  protected readonly loading = signal(false);
  protected readonly message = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly audit = signal<AuditEvent[]>([]);

  constructor() { const user = this.auth.user(); if (user) this.loadAudit(user.role); }

  protected update(field: 'email' | 'displayName' | 'password', event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    if (field === 'email') this.email.set(value);
    if (field === 'displayName') this.displayName.set(value);
    if (field === 'password') this.password.set(value);
  }

  protected submit(event: Event): void {
    event.preventDefault();
    this.loading.set(true);
    this.error.set(null);
    this.message.set(null);
    if (this.mode() === 'register') {
      this.auth.register(this.email(), this.displayName(), this.password()).subscribe({
        next: () => {
          this.message.set('Account created. Signing in…');
          this.login();
        },
        error: (response: HttpErrorResponse) => this.failed(response),
      });
    } else {
      this.login();
    }
  }

  protected logout(): void {
    this.auth.logout();
    this.message.set('Signed out. The access token was removed from memory.');
  }

  protected switchMode(mode: 'login' | 'register'): void {
    this.mode.set(mode);
    this.error.set(null);
    this.message.set(null);
  }

  private login(): void {
    this.auth.login(this.email(), this.password()).subscribe({
      next: (user) => {
        this.loading.set(false);
        this.password.set('');
        this.message.set(`Signed in as ${user.display_name}.`);
        this.loadAudit(user.role);
      },
      error: (response: HttpErrorResponse) => this.failed(response),
    });
  }

  private failed(response: HttpErrorResponse): void {
    this.loading.set(false);
    this.error.set(typeof response.error?.detail === 'string' ? response.error.detail : 'Authentication failed.');
  }

  private loadAudit(role: string): void {
    if (role === 'ADMIN') this.operations.audit().subscribe({ next: (events) => this.audit.set(events) });
  }
}

import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Observable, switchMap, tap } from 'rxjs';

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly token = signal<string | null>(null);
  readonly user = signal<AuthUser | null>(null);
  readonly signedIn = computed(() => this.user() !== null);

  accessToken(): string | null {
    return this.token();
  }

  login(email: string, password: string): Observable<AuthUser> {
    const body = new HttpParams().set('username', email).set('password', password);
    const headers = new HttpHeaders({ 'Content-Type': 'application/x-www-form-urlencoded' });
    return this.http.post<TokenResponse>('/api/v1/auth/token', body.toString(), { headers }).pipe(
      tap((response) => this.token.set(response.access_token)),
      switchMap(() => this.http.get<AuthUser>('/api/v1/auth/me')),
      tap((user) => this.user.set(user)),
    );
  }

  register(
    email: string,
    displayName: string,
    password: string,
  ): Observable<AuthUser> {
    return this.http.post<AuthUser>('/api/v1/auth/register', {
      email,
      display_name: displayName,
      password,
    });
  }

  logout(): void {
    this.token.set(null);
    this.user.set(null);
  }
}

import { DOCUMENT } from '@angular/common';
import { Inject, Injectable, computed, signal } from '@angular/core';

export type Theme = 'light' | 'dark';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly storageKey = 'threatlens-theme';
  readonly theme = signal<Theme>('light');
  readonly isDark = computed(() => this.theme() === 'dark');

  constructor(@Inject(DOCUMENT) private readonly document: Document) {
    const stored = this.readStoredTheme();
    const prefersDark = this.document.defaultView?.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
    this.apply(stored ?? (prefersDark ? 'dark' : 'light'), false);
  }

  toggle(): void { this.apply(this.isDark() ? 'light' : 'dark'); }

  set(theme: Theme): void { this.apply(theme); }

  private apply(theme: Theme, persist = true): void {
    this.theme.set(theme);
    this.document.documentElement.dataset['theme'] = theme;
    this.document.documentElement.style.colorScheme = theme;
    this.document.querySelector('meta[name="theme-color"]')?.setAttribute(
      'content', theme === 'dark' ? '#07111d' : '#0c1c2b',
    );
    if (!persist) return;
    try { this.document.defaultView?.localStorage.setItem(this.storageKey, theme); } catch { /* Storage may be unavailable in hardened browsers. */ }
  }

  private readStoredTheme(): Theme | null {
    try {
      const stored = this.document.defaultView?.localStorage.getItem(this.storageKey);
      return stored === 'light' || stored === 'dark' ? stored : null;
    } catch {
      return null;
    }
  }
}

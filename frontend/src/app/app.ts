import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';

interface NavigationItem { path: string; label: string; icon: string; badge?: string; }

@Component({ selector: 'app-root', imports: [RouterLink, RouterLinkActive, RouterOutlet], templateUrl: './app.html', styleUrl: './app.scss' })
export class App {
  protected readonly auth = inject(AuthService);
  protected readonly menuOpen = signal(false);
  protected readonly navigation: NavigationItem[] = [
    { path: '/', label: 'Overview', icon: '⌂' },
    { path: '/investigations', label: 'Investigations', icon: '⌁' },
    { path: '/intelligence', label: 'Intelligence', icon: '◎' },
    { path: '/sources', label: 'Sources', icon: '◈' },
    { path: '/graph', label: 'Threat graph', icon: '⌘' },
    { path: '/detections', label: 'Detections', icon: '◇' },
    { path: '/cases', label: 'Cases', icon: '□' },
    { path: '/playbooks', label: 'Playbooks', icon: '▷' },
    { path: '/monitoring', label: 'Monitoring', icon: '◉' },
    { path: '/settings', label: 'Settings', icon: '⚙' },
  ];
  protected toggleMenu(): void { this.menuOpen.update((open) => !open); }
  protected closeMenu(): void { this.menuOpen.set(false); }
}

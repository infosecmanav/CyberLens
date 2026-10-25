import { Component, ElementRef, HostListener, ViewChild, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';
import { SecurityIcon } from './core/security-icon';
import { ThemeService } from './core/theme.service';

interface NavigationItem { path: string; label: string; icon: string; description: string; }

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterLinkActive, RouterOutlet, SecurityIcon],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  @ViewChild('commandInput') private commandInput?: ElementRef<HTMLInputElement>;
  protected readonly auth = inject(AuthService);
  protected readonly theme = inject(ThemeService);
  private readonly router = inject(Router);
  protected readonly menuOpen = signal(false);
  protected readonly commandOpen = signal(false);
  protected readonly query = signal('');
  protected readonly navigation: NavigationItem[] = [
    { path: '/', label: 'Overview', icon: 'home', description: 'Operational posture and priorities' },
    { path: '/investigations', label: 'Investigations', icon: 'investigations', description: 'Plan and review evidence-backed investigations' },
    { path: '/intelligence', label: 'Intelligence', icon: 'intelligence', description: 'Look up and normalize entities' },
    { path: '/sources', label: 'Sources', icon: 'sources', description: 'Provider health, access, and capabilities' },
    { path: '/graph', label: 'Threat graph', icon: 'graph', description: 'Explore bounded entity relationships' },
    { path: '/detections', label: 'Detections', icon: 'detections', description: 'Candidate rules and validation coverage' },
    { path: '/cases', label: 'Cases', icon: 'cases', description: 'Analyst tasks, owners, and approvals' },
    { path: '/playbooks', label: 'Playbooks', icon: 'playbooks', description: 'Controlled response procedures' },
    { path: '/monitoring', label: 'Monitoring', icon: 'monitoring', description: 'Objectives and material changes' },
    { path: '/settings', label: 'Settings', icon: 'settings', description: 'Access, policy, and audit events' },
  ];
  protected readonly filteredNavigation = computed(() => {
    const query = this.query().trim().toLowerCase();
    if (!query) return this.navigation;
    return this.navigation.filter((item) => `${item.label} ${item.description}`.toLowerCase().includes(query));
  });

  @HostListener('document:keydown', ['$event'])
  protected handleGlobalKeydown(event: KeyboardEvent): void {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      this.commandOpen() ? this.closeCommand() : this.openCommand();
    } else if (event.key === 'Escape' && this.commandOpen()) {
      this.closeCommand();
    }
  }

  protected toggleMenu(): void { this.menuOpen.update((open) => !open); }
  protected closeMenu(): void { this.menuOpen.set(false); }

  protected openCommand(): void {
    this.commandOpen.set(true);
    queueMicrotask(() => this.commandInput?.nativeElement.focus());
  }

  protected closeCommand(): void { this.commandOpen.set(false); this.query.set(''); }

  protected updateQuery(event: Event): void { this.query.set((event.target as HTMLInputElement).value); }

  protected handleCommandKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && this.filteredNavigation()[0]) this.navigate(this.filteredNavigation()[0].path);
  }

  protected navigate(path: string): void {
    void this.router.navigateByUrl(path);
    this.closeCommand();
    this.closeMenu();
  }
}

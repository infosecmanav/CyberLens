import { provideHttpClient } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';

describe('App', () => {
  let fixture: ComponentFixture<App>;
  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({ imports: [App], providers: [provideHttpClient(), provideRouter([])] }).compileComponents();
    fixture = TestBed.createComponent(App);
    fixture.detectChanges();
  });
  afterEach(() => { fixture.destroy(); localStorage.clear(); document.documentElement.removeAttribute('data-theme'); });
  it('creates the application shell', () => expect(fixture.componentInstance).toBeTruthy());
  it('renders the ThreatLens brand and navigation', () => {
    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('.brand')?.textContent).toContain('ThreatLens');
    expect(element.querySelectorAll('nav a').length).toBe(10);
  });
  it('opens the command palette with the keyboard shortcut', () => {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="dialog"]')).toBeTruthy();
  });
  it('toggles dark mode from the top bar', () => {
    const button = fixture.nativeElement.querySelector('.theme-toggle') as HTMLButtonElement;
    button.click();
    fixture.detectChanges();
    expect(document.documentElement.dataset['theme']).toBe('dark');
  });
});

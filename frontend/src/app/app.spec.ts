import { provideHttpClient } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';

describe('App', () => {
  let fixture: ComponentFixture<App>;
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [App], providers: [provideHttpClient(), provideRouter([])] }).compileComponents();
    fixture = TestBed.createComponent(App);
    fixture.detectChanges();
  });
  it('creates the application shell', () => expect(fixture.componentInstance).toBeTruthy());
  it('renders the ThreatLens brand and navigation', () => {
    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('.brand')?.textContent).toContain('ThreatLens');
    expect(element.querySelectorAll('nav a').length).toBe(10);
  });
});

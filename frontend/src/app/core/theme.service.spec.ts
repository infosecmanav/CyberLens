import { DOCUMENT } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  let service: ThemeService;
  let document: Document;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    document = TestBed.inject(DOCUMENT);
    document.defaultView?.localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    service = TestBed.inject(ThemeService);
  });

  afterEach(() => {
    document.defaultView?.localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.style.removeProperty('color-scheme');
  });

  it('applies an explicit dark theme to the document', () => {
    service.set('dark');
    expect(service.isDark()).toBe(true);
    expect(document.documentElement.dataset['theme']).toBe('dark');
    expect(document.defaultView?.localStorage.getItem('threatlens-theme')).toBe('dark');
  });

  it('toggles back to light mode', () => {
    service.set('dark');
    service.toggle();
    expect(service.theme()).toBe('light');
    expect(document.documentElement.dataset['theme']).toBe('light');
  });
});

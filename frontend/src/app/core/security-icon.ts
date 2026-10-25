import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-security-icon',
  template: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      @switch (name) {
        @case ('home') { <path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v10h13V10M9 20v-6h6v6"/> }
        @case ('investigations') { <circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5M10.5 7v7M7 10.5h7"/> }
        @case ('intelligence') { <circle cx="12" cy="12" r="3"/><path d="M3.5 12s3-6 8.5-6 8.5 6 8.5 6-3 6-8.5 6-8.5-6-8.5-6Z"/> }
        @case ('sources') { <path d="M5 5.5h14v13H5zM8 2.5h8M8 21.5h8"/><path d="M8 9h8M8 13h5"/> }
        @case ('graph') { <circle cx="5" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="m7.3 10.9 8.4-3.8M7.3 13.1l8.4 3.8M18 8.5v7"/> }
        @case ('detections') { <path d="M12 3 3.5 7v5c0 5.3 3.6 8.2 8.5 9 4.9-.8 8.5-3.7 8.5-9V7L12 3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/> }
        @case ('cases') { <rect x="3.5" y="6" width="17" height="14" rx="2"/><path d="M8 6V4h8v2M3.5 11h17M10 11v2h4v-2"/> }
        @case ('playbooks') { <path d="M6 3.5h12v17H6zM9 3.5v17"/><path d="m12.5 9 3 2-3 2V9Z"/> }
        @case ('monitoring') { <path d="M3 12h4l2-5 4 10 2-5h6"/><circle cx="12" cy="12" r="9"/> }
        @case ('settings') { <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/> }
        @case ('search') { <circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/> }
        @case ('moon') { <path d="M20.5 15.5A8 8 0 0 1 8.5 3.8 8.5 8.5 0 1 0 20.5 15.5Z"/> }
        @case ('sun') { <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/> }
        @case ('bell') { <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/> }
        @default { <circle cx="12" cy="12" r="8"/> }
      }
    </svg>
  `,
  styles: [':host{display:inline-grid;width:20px;height:20px;place-items:center}:host svg{width:100%;height:100%}'],
})
export class SecurityIcon { @Input({ required: true }) name = ''; }

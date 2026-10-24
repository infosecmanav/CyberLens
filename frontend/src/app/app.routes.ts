import { Routes } from '@angular/router';
import { Dashboard } from './pages/dashboard/dashboard';

export const routes: Routes = [
  { path: '', component: Dashboard, title: 'Overview · ThreatLens' },
  { path: 'sources', loadComponent: () => import('./pages/sources/sources').then((module) => module.Sources), title: 'Sources · ThreatLens' },
  { path: 'investigations', loadComponent: () => import('./pages/investigations/investigations').then((module) => module.Investigations), title: 'Investigations · ThreatLens' },
  { path: 'intelligence', loadComponent: () => import('./pages/intelligence/intelligence').then((module) => module.Intelligence), title: 'Intelligence · ThreatLens' },
  { path: 'graph', loadComponent: () => import('./pages/graph/graph').then((module) => module.Graph), title: 'Threat graph · ThreatLens' },
  { path: 'detections', loadComponent: () => import('./pages/detections/detections').then((module) => module.Detections), title: 'Detections · ThreatLens' },
  { path: 'cases', loadComponent: () => import('./pages/cases/cases').then((module) => module.Cases), title: 'Cases · ThreatLens' },
  { path: 'playbooks', loadComponent: () => import('./pages/playbooks/playbooks').then((module) => module.Playbooks), title: 'Playbooks · ThreatLens' },
  { path: 'monitoring', loadComponent: () => import('./pages/monitoring/monitoring').then((module) => module.Monitoring), title: 'Monitoring · ThreatLens' },
  { path: 'settings', loadComponent: () => import('./pages/settings/settings').then((module) => module.Settings), title: 'Settings · ThreatLens' },
  { path: '**', redirectTo: '' },
];

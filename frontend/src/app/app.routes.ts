import { Routes } from '@angular/router';
import { Dashboard } from './pages/dashboard/dashboard';
import { Intelligence } from './pages/intelligence/intelligence';
import { Placeholder } from './pages/placeholder/placeholder';
import { Sources } from './pages/sources/sources';

export const routes: Routes = [
  { path: '', component: Dashboard, title: 'Overview · ThreatLens' },
  { path: 'sources', component: Sources, title: 'Sources · ThreatLens' },
  { path: 'investigations', component: Placeholder, title: 'Investigations · ThreatLens', data: { title: 'Investigations', phase: 'Phase 3', description: 'Evidence-backed investigation workflows are prepared for the next implementation phase.' } },
  { path: 'intelligence', component: Intelligence, title: 'Intelligence · ThreatLens' },
  { path: 'graph', component: Placeholder, title: 'Threat graph · ThreatLens', data: { title: 'Threat graph', phase: 'Phase 4', description: 'Evidence-backed relationships and bounded graph exploration are planned here.' } },
  { path: 'detections', component: Placeholder, title: 'Detections · ThreatLens', data: { title: 'Detections', phase: 'Phase 6', description: 'Draft detection candidates, technique coverage, and validation state will appear here.' } },
  { path: 'cases', component: Placeholder, title: 'Cases · ThreatLens', data: { title: 'Cases', phase: 'Phase 7', description: 'Analyst cases, tasks, decisions, and audit history will appear here.' } },
  { path: 'playbooks', component: Placeholder, title: 'Playbooks · ThreatLens', data: { title: 'Playbooks', phase: 'Phase 7', description: 'Controlled workflows and approval-gated response actions will appear here.' } },
  { path: 'monitoring', component: Placeholder, title: 'Monitoring · ThreatLens', data: { title: 'Monitoring', phase: 'Phase 8', description: 'Saved objectives, collection schedules, and meaningful intelligence changes will appear here.' } },
  { path: 'settings', component: Placeholder, title: 'Settings · ThreatLens', data: { title: 'Settings', phase: 'Foundation', description: 'Workspace policy, access control, and connector configuration belong here.' } },
  { path: '**', redirectTo: '' },
];

import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { EntityListResponse } from './intelligence.models';
import {
  AuditEvent,
  CaseRecord,
  CaseTask,
  ApprovalRequest,
  Detection,
  DetectionCoverage,
  Evidence,
  IntelligenceChange,
  Investigation,
  InvestigationGraph,
  InvestigationList,
  MonitoringObjective,
  MonitoringRun,
  OperationsMetrics,
  Playbook,
  PlaybookExecution,
  Similarity,
} from './operations.models';

@Injectable({ providedIn: 'root' })
export class OperationsService {
  private readonly http = inject(HttpClient);

  investigations(): Observable<InvestigationList> { return this.http.get<InvestigationList>('/api/v1/investigations'); }
  investigation(id: string): Observable<Investigation> { return this.http.get<Investigation>(`/api/v1/investigations/${id}`); }
  createInvestigation(payload: Record<string, unknown>): Observable<Investigation> { return this.http.post<Investigation>('/api/v1/investigations', payload); }
  runInvestigation(id: string): Observable<Investigation> { return this.http.post<Investigation>(`/api/v1/investigations/${id}/run`, {}); }
  reconcileInvestigation(id: string): Observable<Investigation> { return this.http.post<Investigation>(`/api/v1/investigations/${id}/reconcile`, {}); }
  cancelInvestigation(id: string): Observable<Investigation> { return this.http.post<Investigation>(`/api/v1/investigations/${id}/cancel`, {}); }
  resumeInvestigation(id: string): Observable<Investigation> { return this.http.post<Investigation>(`/api/v1/investigations/${id}/resume`, {}); }
  recordDecision(id: string, verdict: string, rationale: string): Observable<Record<string, unknown>> { return this.http.post<Record<string, unknown>>(`/api/v1/investigations/${id}/decisions`, { verdict, rationale }); }
  evidence(id: string): Observable<Evidence[]> { return this.http.get<Evidence[]>(`/api/v1/investigations/${id}/evidence`); }
  graph(id: string): Observable<InvestigationGraph> { return this.http.get<InvestigationGraph>(`/api/v1/investigations/${id}/graph`); }
  similar(id: string): Observable<Similarity[]> { return this.http.get<Similarity[]>(`/api/v1/investigations/${id}/similar`); }

  detections(): Observable<Detection[]> { return this.http.get<Detection[]>('/api/v1/detections'); }
  createDetection(payload: Record<string, unknown>): Observable<Detection> { return this.http.post<Detection>('/api/v1/detections', payload); }
  validateDetection(id: string, payload: Record<string, unknown>): Observable<Detection> { return this.http.post<Detection>(`/api/v1/detections/${id}/validations`, payload); }
  detectionCoverage(): Observable<DetectionCoverage> { return this.http.get<DetectionCoverage>('/api/v1/detections/coverage'); }

  cases(): Observable<CaseRecord[]> { return this.http.get<CaseRecord[]>('/api/v1/cases'); }
  createCase(payload: Record<string, unknown>): Observable<CaseRecord> { return this.http.post<CaseRecord>('/api/v1/cases', payload); }
  tasks(caseId: string): Observable<CaseTask[]> { return this.http.get<CaseTask[]>(`/api/v1/cases/${caseId}/tasks`); }
  createTask(caseId: string, payload: Record<string, unknown>): Observable<CaseTask> { return this.http.post<CaseTask>(`/api/v1/cases/${caseId}/tasks`, payload); }
  executeTask(taskId: string): Observable<CaseTask> { return this.http.post<CaseTask>(`/api/v1/cases/tasks/${taskId}/execute`, {}); }
  requestApproval(taskId: string, riskSummary: string): Observable<ApprovalRequest> { return this.http.post<ApprovalRequest>(`/api/v1/cases/tasks/${taskId}/approval`, { risk_summary: riskSummary }); }
  resolveApproval(id: string, status: 'APPROVED' | 'REJECTED', rationale: string): Observable<ApprovalRequest> { return this.http.post<ApprovalRequest>(`/api/v1/cases/approvals/${id}/resolve`, { status, rationale }); }

  playbooks(): Observable<Playbook[]> { return this.http.get<Playbook[]>('/api/v1/playbooks'); }
  executePlaybook(id: string): Observable<PlaybookExecution> { return this.http.post<PlaybookExecution>(`/api/v1/playbooks/${id}/executions`, { dry_run: true }); }

  objectives(): Observable<MonitoringObjective[]> { return this.http.get<MonitoringObjective[]>('/api/v1/monitoring'); }
  createObjective(payload: Record<string, unknown>): Observable<MonitoringObjective> { return this.http.post<MonitoringObjective>('/api/v1/monitoring', payload); }
  runObjective(id: string): Observable<MonitoringRun> { return this.http.post<MonitoringRun>(`/api/v1/monitoring/${id}/run`, {}); }
  changes(): Observable<IntelligenceChange[]> { return this.http.get<IntelligenceChange[]>('/api/v1/monitoring/changes'); }
  acknowledgeChange(id: string): Observable<IntelligenceChange> { return this.http.post<IntelligenceChange>(`/api/v1/monitoring/changes/${id}/acknowledge`, {}); }
  entities(): Observable<EntityListResponse> { return this.http.get<EntityListResponse>('/api/v1/intelligence/entities', { params: { limit: 100 } }); }

  metrics(): Observable<OperationsMetrics> { return this.http.get<OperationsMetrics>('/api/v1/operations/metrics'); }
  audit(): Observable<AuditEvent[]> { return this.http.get<AuditEvent[]>('/api/v1/audit'); }
}

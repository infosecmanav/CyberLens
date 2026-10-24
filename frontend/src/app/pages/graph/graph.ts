import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import cytoscape, { Core, ElementDefinition } from 'cytoscape';
import { Investigation, InvestigationGraph } from '../../core/operations.models';
import { OperationsService } from '../../core/operations.service';

@Component({ selector: 'app-graph', imports: [RouterLink], templateUrl: './graph.html', styleUrl: './graph.scss' })
export class Graph implements AfterViewInit, OnDestroy {
  @ViewChild('graphCanvas') private graphCanvas!: ElementRef<HTMLDivElement>;
  private readonly operations = inject(OperationsService);
  private graph: Core | null = null;
  private viewReady = false;
  protected readonly investigations = signal<Investigation[]>([]);
  protected readonly selected = signal<Investigation | null>(null);
  protected readonly data = signal<InvestigationGraph | null>(null);
  protected readonly error = signal<string | null>(null);

  constructor() {
    this.operations.investigations().subscribe({
      next: (response) => this.investigations.set(response.items),
      error: () => this.error.set('Investigations could not be loaded.'),
    });
  }

  ngAfterViewInit(): void { this.viewReady = true; }
  ngOnDestroy(): void { this.graph?.destroy(); }

  protected load(item: Investigation): void {
    this.selected.set(item);
    this.error.set(null);
    this.operations.graph(item.id).subscribe({
      next: (data) => { this.data.set(data); this.render(data); },
      error: () => this.error.set('The evidence graph could not be loaded.'),
    });
  }

  protected friendly(value: string): string { return value.replaceAll('_', ' ').toLowerCase(); }

  private render(data: InvestigationGraph): void {
    if (!this.viewReady) return;
    this.graph?.destroy();
    const elements: ElementDefinition[] = [
      ...data.nodes.map((node) => ({ data: { id: node.id, label: node.value, type: node.entity_type, role: node.role } })),
      ...data.edges.map((edge) => ({ data: { id: edge.id, source: edge.source, target: edge.target, label: this.friendly(edge.relationship_type) } })),
    ];
    this.graph = cytoscape({
      container: this.graphCanvas.nativeElement,
      elements,
      layout: { name: 'cose', animate: false, padding: 35 },
      style: [
        { selector: 'node', style: { 'background-color': '#43c89f', color: '#29475b', label: 'data(label)', 'font-size': 9, 'text-valign': 'bottom', 'text-margin-y': 7, width: 24, height: 24 } },
        { selector: 'node[role = "seed"]', style: { 'background-color': '#287c91', width: 34, height: 34 } },
        { selector: 'edge', style: { width: 1.5, 'line-color': '#9cb7c1', 'target-arrow-color': '#9cb7c1', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', label: 'data(label)', 'font-size': 7, color: '#748995', 'text-background-color': '#ffffff', 'text-background-opacity': 1 } },
      ],
    });
  }
}

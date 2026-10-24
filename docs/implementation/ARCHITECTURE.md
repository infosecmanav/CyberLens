# ThreatLens architecture

## Runtime shape

```text
Angular analyst workspace
          │ /api/v1
          ▼
FastAPI routes and RBAC
          │
          ├── connector manager ── verified remote sources
          ├── investigation planner and executor
          ├── correlation and similarity
          └── monitoring scheduler
          │ async SQLAlchemy
          ▼
PostgreSQL and Alembic
```

FastAPI owns provider credentials, normalization, authorization, collection policy, budgets, and persistence. Provider secrets never reach Angular. The first registered user is an administrator; later users are analysts. Read routes expose current workspace state, while collection and operational mutations require an authenticated analyst. Production validation and approval resolution require an administrator.

## Backend boundaries

- `app/api`: versioned routes, request validation, RBAC dependencies, and response schemas.
- `app/core`: environment settings and security primitives.
- `app/db`: declarative metadata and async database lifecycle.
- `app/models`: users, intelligence lineage, investigations, detections, cases, approvals, monitoring, and audit records.
- `app/intelligence`: catalogue, normalization, connector contracts, capability routing, limits, caching, and explicit outcomes.
- `app/investigations`: deterministic planning and idempotent step execution.
- `app/correlation`: bounded graph traversal and transparent Jaccard similarity.
- `app/operations`: audit emission, default playbook seeding, and monitoring execution.

## Investigation flow

Each investigation receives the same five ordered phases: planning, collection, enrichment, correlation, and assessment. Objective text is stored as untrusted analyst context; it cannot add tools or alter the planner. Runtime, request, entity, graph, pivot, report, and cost budgets are persisted with usage. A failed or exhausted step enters an explicit error or analyst-waiting state and can resume without repeating completed work.

Connector results become observations before an analyst or engine promotes them to evidence. Findings cite evidence. Assessments store source coverage, corroboration, temporal relevance, and analytical consistency separately instead of compressing them into an unexplained score. Similarity records shared factors and states that overlap does not prove attribution.

## Operational controls

Detection candidates require existing evidence and documented telemetry, false positives, assumptions, and limits. Cases and playbooks emit audit events. All task and playbook execution is dry-run. High-impact work enters `WAITING_APPROVAL`; only an administrator can resolve its approval record.

Monitoring uses an in-process scheduler for a single-instance development deployment. Each run fingerprints current source-backed state. The first result creates a baseline, matching fingerprints create non-actionable duplicate records, and relationship changes create actionable records. A multi-instance deployment should move scheduling and rate-limit state to durable infrastructure.

## Trust boundaries

Remote intelligence, reports, provider failures, and investigation objectives are untrusted input. Raw responses are retained as provenance but never gain application authority. Missing, forbidden, limited, timed-out, malformed, and empty provider responses remain distinct. Active scanning, submitted-URL browsing, malware downloads, paid operations, destructive response actions, and autonomous attribution are outside the implemented boundary.

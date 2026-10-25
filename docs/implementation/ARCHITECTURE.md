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

## Intelligence interoperability path

The connector contract is the extension boundary for future feed frameworks and TAXII services. A feed adapter must translate external records into the existing entity, provider-record, observation, and evidence lineage rather than bypassing those controls. Imports must preserve the producer, retrieval time, external identifier, confidence or marking when present, raw provenance, and an explicit parse outcome.

GOSINT and OpenTAXII are research references for the interoperability backlog. They are not implemented integrations and are not data sources by themselves. Before compatibility is advertised, the project will verify the current upstream project status, supported protocol versions, licensing, authentication behavior, and representative payloads. The planned delivery slices and acceptance criteria are recorded in the [intelligence interoperability backlog](INTELLIGENCE_INTEROPERABILITY_BACKLOG.md).

Version 1.2 implements the first local interoperability boundary: an authenticated analyst can submit a bounded STIX 2.1 JSON bundle. The importer accepts a documented subset of single-IoC Indicator equality patterns, routes values through canonical normalization, stores the complete STIX object as the provider record, carries producer/marking/confidence metadata into the observation, reports unsupported or invalid objects, and emits an audit event. It performs no network requests and does not claim TAXII compatibility.

Version 1.3 makes that boundary durable. Every submission creates an import batch containing the bundle hash, contract, source, submitter, counts, status, and completion time. Each object creates an ordered outcome. Imported or deduplicated outcomes link to the canonical entity and observation; rejected or skipped outcomes retain the bounded raw object and content hash as a quarantine record. Batch history is authenticated and filterable by status or the presence of issues.

Version 1.4 applies an optional, validated filter after STIX parsing and before persistence. The filter can constrain supported entity types, minimum confidence, an inclusive `valid_from` window, and required marking references. Filtered objects create ordered `FILTERED` outcomes without creating entities or observations. Invalid objects remain rejected and unsupported objects remain skipped, so filtering cannot conceal parsing failures. The canonical filter definition and filtered count are stored with the batch and returned by the immediate and historical APIs.

## Operational controls

Detection candidates require existing evidence and documented telemetry, false positives, assumptions, and limits. Cases and playbooks emit audit events. All task and playbook execution is dry-run. High-impact work enters `WAITING_APPROVAL`; only an administrator can resolve its approval record.

Monitoring uses an in-process scheduler for a single-instance development deployment. Each run fingerprints current source-backed state. The first result creates a baseline, matching fingerprints create non-actionable duplicate records, and relationship changes create actionable records. A multi-instance deployment should move scheduling and rate-limit state to durable infrastructure.

## Trust boundaries

Remote intelligence, reports, provider failures, and investigation objectives are untrusted input. Raw responses are retained as provenance but never gain application authority. Missing, forbidden, limited, timed-out, malformed, and empty provider responses remain distinct. Active scanning, submitted-URL browsing, malware downloads, paid operations, destructive response actions, and autonomous attribution are outside the implemented boundary.

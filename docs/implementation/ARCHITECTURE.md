# ThreatLens architecture

## Runtime shape

ThreatLens is a monorepo with three current runtime components:

```text
Angular browser app
       │ /api
       ▼
FastAPI application
       │ async SQLAlchemy
       ▼
PostgreSQL
```

FastAPI owns credentials, provider calls, normalization, authorization, and persistence. Provider secrets must never reach the browser. Angular consumes typed API responses and presents missing-key, unsupported, unavailable, and quota-limited states distinctly.

## Backend boundaries

- `app/api`: versioned HTTP routes and request dependencies.
- `app/core`: environment configuration and security primitives.
- `app/db`: declarative metadata and async database lifecycle.
- `app/models`: persisted users, sources, entities, provenance, evidence, and relationships.
- `app/intelligence/catalog.py`: canonical source inventory. Inventory does not imply implementation.
- `app/intelligence/connectors`: provider-neutral contracts, capability routing, execution limits, and normalized outcomes.
- `app/intelligence/normalization`: reserved boundary for Phase 2 canonicalization.

Every connector declares capabilities. The manager selects providers by operation and entity type rather than calling every provider. Failures return explicit outcomes; a missing credential, timeout, or empty response is never interpreted as evidence that an entity is benign.

## Trust boundaries

Remote intelligence, reports, and provider errors are untrusted input. Raw data is retained as provenance but does not acquire application authority. Active scans, URL submissions, malware downloads, destructive response actions, and paid operations remain disabled unless an explicit later policy permits them.

JWT authentication provides the Phase 1 identity boundary. Later phases will add administrative user provisioning, fine-grained authorization, session controls, and comprehensive audit emission.

## Evolution

Phase 2 adds verified connectors, normalization, caching, rate limits, and source health without changing the base connector contract. Later phases add durable investigations, evidence correlation, graph exploration, detections, cases, playbooks, and monitoring in sequence.


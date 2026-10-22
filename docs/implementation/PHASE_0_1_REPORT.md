# Phase 0–1 completion report

## Completed

- Established the Python 3.12 FastAPI and Angular 20 monorepo.
- Added Dockerfiles, Docker Compose, PostgreSQL 17, local proxying, configuration, and ignored secret files.
- Added a versioned API, OpenAPI docs, liveness/readiness, CORS, JWT authentication, Argon2 hashes, and role-ready users.
- Added the initial Alembic migration and verified it has no drift from SQLAlchemy metadata on PostgreSQL.
- Added foundational source, capability, entity, observation, evidence, relationship, and audit models.
- Added all sources named in the requirements to one inventory with provisional status rather than fabricated support.
- Added a provider-neutral connector contract, registry, capability selection, concurrency limit, timeout handling, and explicit outcomes.
- Added one local fixture connector whose output is explicitly labelled demonstration-only.
- Added a responsive Angular shell, overview dashboard, Source Registry with live API state, filters, truthful statuses, and planned navigation.
- Added backend and frontend tests and production frontend build validation.

## Current limitations

- No external provider connector is implemented or live-tested yet.
- Provider documentation, free/commercial terms, authentication, quotas, caching, and attribution rules are provisional until Phase 2 review.
- Authentication supports self-registration for development; administration, invitation, password reset, and full RBAC remain future work.
- Redis and durable background jobs are reserved for later phases and are not required by the current synchronous foundation workflow.
- Investigation, graph, detection, case, playbook, and monitoring routes are visible architecture boundaries, not completed features.

## Exact next tasks: Phase 2

1. Implement canonical IOC validation and normalization with deterministic entity keys.
2. Add persisted source records, collection jobs, cache entries, quota state, and source-health events through a new migration.
3. Verify official documentation and licensing for the first bounded group: CISA KEV, NVD, CVE.org, OSV, MITRE ATT&CK, OTX, VirusTotal, and abuse.ch.
4. Implement unauthenticated public datasets first, then credential-aware connectors that return `NOT_CONFIGURED` without blocking other sources.
5. Add fixture-based connector tests for every outcome and opt-in live tests for supplied keys.
6. Add entity lookup APIs and Angular intelligence search using persisted observations and provenance.
7. Update `docs/SOURCE_MATRIX.md` only from verified evidence; do not promote scaffolded sources to implemented.


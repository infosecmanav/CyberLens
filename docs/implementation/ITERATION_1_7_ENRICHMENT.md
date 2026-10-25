# Iteration 1.7 — automated enrichment workflows

Date: 2026-10-25

## Outcome

ThreatLens administrators can schedule bounded enrichment of new canonical entities through explicitly selected connectors. Every result keeps its source attribution and collection-job lineage. Automation produces observations only; analyst promotion remains the sole path to reviewed evidence.

## Delivered behavior

- Policies define a unique name, one or more entity types, one or more registered source connectors, a cadence, and a maximum of 100 entities per run.
- Policy creation validates connector availability and entity-type capability. The labelled local-fixture connector is prohibited from automated workflows.
- Each policy processes canonical entities once in deterministic creation order. Later runs select only records that have not already received a policy item.
- Each entity retains the underlying collection job, status, source outcomes, all returned observation IDs, and the subset newly persisted by that run.
- Run totals distinguish candidates, processed entities, new observations, and connector outcomes such as success, no result, rate limit, authentication failure, or network error.
- `NO_RESULT` records the source outcome without creating an observation, evidence, or benign verdict.
- Enabled policies run on the shared bounded scheduler. Administrators can pause, resume, and trigger the same workflow manually.
- The dark/light Settings console shows policy scopes, budgets, cadence, schedule state, recent outcomes, and the evidence boundary.

## Verification

- API tests cover allowlist validation, demonstration-source rejection, successful enrichment lineage, once-per-policy behavior, durable run history, and `NO_RESULT` semantics.
- Frontend service tests cover policy creation, pause/resume configuration, and manual execution endpoints.
- The complete backend regression suite, Ruff, strict mypy, Angular unit suite, production build, PostgreSQL migration parity, Docker health checks, and representative OpenAPI requests are required before release.

## Boundary

The included UI exposes the currently registered vulnerability connectors, CISA KEV and OSV, for CVE enrichment. Live provider availability and access limits remain visible source outcomes. An enrichment result never changes an assessment or evidence state by itself.

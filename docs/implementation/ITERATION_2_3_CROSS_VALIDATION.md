# Iteration 2.3 — provenance-aware cross-validation

Date: 2026-10-26

ThreatLens 2.3 strengthens investigation assessment by distinguishing provider count from independent upstream provenance.

## Delivered

- Added a deterministic evidence-reconciliation engine with explicit `NO_EVIDENCE`, `SINGLE_SOURCE`, `MULTI_SOURCE_CONTEXT`, `SHARED_UPSTREAM_REPORTING`, `INDEPENDENT_CORROBORATION`, and `CONFLICTING_EVIDENCE` states.
- Normalized exact source and upstream references before grouping, so superficial trailing-slash or hostname-case differences do not inflate independence.
- Persisted provider, provenance-group, polarity, shared-upstream, and limitation counts on each assessment through Alembic revision `20261026_0011`.
- Replaced the previous direct-provider count with an independent-provenance dimension that explains both values.
- Added an authenticated reconciliation endpoint for recalculating older completed investigations from their persisted observations and evidence without recollecting provider data.
- Added a responsive evidence panel that displays provider and provenance counts, supporting and conflicting evidence, shared upstream references, and analytical limitations in light and dark themes.

## Analytical boundary

Cross-validation does not produce a probability. Matching references establish shared reporting, not independent corroboration. Different references are treated as distinct provenance groups, but analysts must still judge whether organizational or reporting relationships make them dependent. Conflicting provider claims remain visible and never automatically establish benignity.

## Validation focus

Tests cover empty evidence, normalized reference grouping, shared-upstream repetition across MISP-style providers, independent supporting provenance, contradictory polarity, persisted assessment snapshots, idempotent reconciliation, and the analyst-facing API result. Routine tests use fixtures and consume no provider quota.

## Release validation

- Ruff passed across the backend repository.
- Strict mypy passed across 95 source files.
- Pytest passed: 126 tests, with one upstream Starlette deprecation warning.
- Frontend tests passed: 22 tests.
- The Angular production build passed at 350.42 kB initial bundle size; the investigations lazy chunk is 23.06 kB.
- The production dependency audit reported zero vulnerabilities.
- Docker Compose rendered successfully and all three development services became healthy or ready.
- Direct and frontend-proxied health checks reported ThreatLens `2.3.0`, and the live OpenAPI document included the reconciliation route.
- The existing PostgreSQL database reached Alembic revision `20261026_0011` with no schema drift.
- A clean disposable PostgreSQL database replayed all 11 migrations, reached `20261026_0011`, and reported no schema drift.

# Iteration 2.4 — analytical-dimension alignment

Date: 2026-10-27

ThreatLens 2.4 prevents provenance-aware cross-validation from treating evidence about different claims as corroboration or contradiction.

## Delivered

- Added an explicit analytical dimension to every evidence record, with a migration that conservatively backfills existing evidence from normalized observation types.
- Added dimensions for maliciousness, vulnerability context, malware association, infrastructure association, behavioral association, threat-actor attribution, detection applicability, and general context.
- Updated engine-created evidence to classify known observation contracts while leaving unknown or broad records as general context.
- Updated analyst evidence promotion to require a visible dimension selection and include it in API responses and audit details.
- Reconciled provenance, polarity, and provider counts within each dimension. Overall corroboration now requires at least two supporting provenance groups in the same dimension.
- Scoped conflict to evidence that supports and disputes the same dimension. Cross-dimension disagreement remains visible without automatically negating another claim.
- Added a responsive, theme-aware dimension matrix to the investigation evidence panel and labelled each evidence card with its dimension.

## Analytical boundary

Dimensions are deterministic categories, not semantic proof that two natural-language claims are identical. General-context evidence remains deliberately broad. Analysts must review claim wording, source relationships, time relevance, and organizational dependence before making a decision. Reconciliation does not produce a probability.

## Validation focus

Validation covers conservative observation mapping, same-dimension corroboration and conflict, cross-dimension support separation, cross-dimension disagreement, shared-upstream collapse, analyst-selected dimensions, migration backfill, persisted reconciliation, and the investigation API and UI contracts.

## Release validation

- Ruff passed across the backend repository.
- Strict mypy passed across 95 source files.
- Pytest passed: 129 tests, with one upstream Starlette deprecation warning.
- Frontend tests passed: 22 tests.
- The Angular production build passed at 350.42 kB initial bundle size; intelligence and investigation remain lazy chunks at 57.45 kB and 24.87 kB.
- The production dependency audit reported zero vulnerabilities.
- Docker Compose rendered and rebuilt successfully, and all three development services became healthy or ready.
- Direct and frontend-proxied readiness checks reported ThreatLens `2.4.0` with the database ready. The live OpenAPI document exposed evidence dimensions and the reconciliation endpoint.
- The live PostgreSQL database reached Alembic revision `20261027_0012` with no schema drift.
- A disposable PostgreSQL database replayed the first 11 migrations, accepted three pre-2.4 evidence fixtures, and then upgraded to revision `0012`. The backfill classified known exploitation as maliciousness, malware sample context as malware association, and an unknown observation as general context before reporting no schema drift.

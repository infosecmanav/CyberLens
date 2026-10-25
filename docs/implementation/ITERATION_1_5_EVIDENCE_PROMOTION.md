# Iteration 1.5 — analyst evidence promotion

Date: 2026-10-25

## Iteration goal

Keep collection separate from analytical judgment. Accepted STIX observations become evidence only after an authenticated analyst records a bounded claim, polarity, and uncertainty.

## User stories and acceptance criteria

### Explicit promotion

As an analyst, I can promote a reviewed import outcome so later findings and detections can cite it as evidence.

- Only `IMPORTED` or `DEDUPLICATED` outcomes with a surviving observation are eligible.
- Promotion records `SUPPORTS`, `CONFLICTS`, or `CONTEXTUAL` polarity, a meaningful claim, explicit uncertainty notes, reviewer identity, and review time.
- The source observation remains unchanged and continues to preserve upstream provenance.
- Filtered, rejected, and skipped outcomes cannot be promoted.
- A single import outcome cannot be promoted twice.

### Traceability and metrics

As an analyst, I can trace the judgment from an import report into the evidence layer.

- The import outcome stores its evidence link and the batch increments its promoted count atomically.
- Promotion emits an audit event containing the import, outcome, observation, evidence, actor, and polarity.
- History can filter batches with or without promotions.
- Existing engine-created evidence remains distinguishable because it has no analyst promoter.

### Analyst console

As an analyst, I can complete the review inside the Intelligence workspace.

- Accepted outcomes expose an explicit promotion action; ineligible outcomes do not.
- The review form requires polarity, a claim, and uncertainty before submission.
- Recorded evidence is shown with its durable identifier and cannot be submitted again.
- The ledger includes promoted counts and all/promoted/unreviewed filters in light and dark modes.

## Verification

- 63 backend tests pass, covering authorization, eligibility, persisted review context, duplicate and ineligible rejection, promoted counts, history filtering, audit output, and reuse of promoted evidence by detection engineering.
- Ruff and strict mypy pass across 57 backend source modules.
- 12 frontend tests pass, including the promotion and history-filter service contracts.
- The warning-free Angular production build passes at 350.18 kB initial raw size; the lazy Intelligence chunk is 56.42 kB.
- PostgreSQL upgraded to `20261025_0006`; `alembic check` reports no pending operations.
- The production npm audit reports zero vulnerabilities.
- Fresh backend and frontend Docker images build successfully. The recreated stack reports ThreatLens 1.5.0 ready with its database available.
- Live OpenAPI exposes the authenticated promotion endpoint and `has_promotions` history filter. An unauthenticated promotion returns HTTP 401.

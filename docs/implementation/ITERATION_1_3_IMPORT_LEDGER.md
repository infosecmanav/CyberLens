# Iteration 1.3 — durable import ledger

Date: 2026-10-25

## Iteration goal

Make STIX import outcomes reviewable after the immediate API response. Analysts need a durable record of each submitted bundle and each object disposition before automated feed collection or filtering expands the ingestion volume.

## User stories and acceptance criteria

### Import history

As an analyst, I can reopen recent imports so I can review what entered the workspace and what required attention.

- Every submission creates a distinct batch with its bundle ID and hash, source, submitter, active contract, timestamps, status, and aggregate counts.
- Reimporting identical content creates a new audit batch while reusing existing source records and observations.
- Authenticated history supports status and issue-presence filters plus bounded pagination.
- Detail responses return object outcomes in original bundle order.

### Quarantined outcomes

As an analyst, I can inspect rejected or skipped objects without treating them as evidence.

- Imported and deduplicated outcomes reference their canonical entity and observation.
- Rejected and skipped outcomes retain their raw bounded object, hash, code, and explanatory message.
- Accepted raw objects remain in the existing source-record lineage instead of being duplicated in the quarantine table.
- Deleting a linked entity or observation preserves the historical outcome and clears only the optional link.

### Analyst console

As an analyst, I can review recent batch status and ordered object outcomes from the Intelligence workspace.

- The history component loads only authenticated data and silently stays absent for signed-out users.
- A completed import refreshes the ledger without reloading the page.
- Status, accepted/received totals, new/reused totals, object codes, and messages remain readable in light and dark modes.

## Verification

- 55 backend tests cover the full baseline plus import persistence, history authorization, status and issue filters, and quarantine records.
- Ruff and strict mypy pass across 57 backend source files.
- 12 frontend tests cover the shell, themes, dashboard, intelligence calls, import submission, and ledger request contracts.
- The Angular production build passes at 349.28 kB initial raw size.
- PostgreSQL upgraded to `20261025_0004`; `alembic check` reports no pending operations.
- The production npm audit reports zero vulnerabilities.
- Fresh backend and frontend Docker images build successfully. The recreated stack reports ThreatLens 1.3.0 ready with its database available.
- The frontend proxy exposes readiness and both authenticated history routes. An unauthenticated history request returns HTTP 401.

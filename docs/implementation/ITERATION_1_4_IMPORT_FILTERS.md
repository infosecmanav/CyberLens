# Iteration 1.4 — reproducible import filters

Date: 2026-10-25

## Iteration goal

Reduce manual STIX feed noise with visible, reproducible criteria while preserving validation failures and provenance. This is the first vertical increment of interoperability Slice 3.

## User stories and acceptance criteria

### Filter definition

As an analyst, I can constrain a bundle before persistence so only relevant validated indicators enter the workspace.

- Optional criteria cover the eight supported observable types, minimum confidence from 0 through 100, an inclusive `valid_from` window, and required STIX marking-definition references.
- All criteria combine with logical AND. An indicator must contain every requested marking reference.
- Definitions reject unsupported types, duplicate values, malformed marking IDs, timezone-free timestamps, reversed windows, and out-of-range confidence.
- Empty criteria preserve the version 1.3 import behavior.

### Reproducible outcomes

As an analyst, I can explain why an object was excluded and rerun the same policy later.

- The batch stores a canonical filter definition and a separate filtered-object count.
- Filtered indicators create ordered outcomes with a stable code, explanation, content hash, and bounded raw record.
- Filtered indicators do not create entities, source records, or observations.
- Parsing precedes filtering. Invalid indicators remain rejected and unsupported object types remain skipped.
- Expected filtering does not mark an otherwise clean batch as having processing issues.

### Analyst console

As an analyst, I can configure and inspect filters without leaving the Intelligence workspace.

- A responsive filter rail provides type chips and confidence, time-window, and marking controls.
- Active-criteria counts and a clear action make the current state visible.
- Immediate reports distinguish received, accepted, filtered, rejected, and skipped objects.
- History detail displays the saved filter and highlights filtered outcomes in light and dark modes.

## Verification

- 62 backend tests pass, covering every filter criterion, validation failures, canonical persistence, raw filtered outcomes, clean-batch status, and empty-filter compatibility.
- Ruff and strict mypy pass across 57 backend source modules.
- 12 frontend tests pass, including the filter request/response service contract.
- The warning-free Angular production build passes at 349.89 kB initial raw size; the lazy Intelligence chunk is 48.41 kB.
- PostgreSQL upgraded to `20261025_0005`; `alembic check` reports no pending operations.
- The production npm audit reports zero vulnerabilities.
- Fresh backend and frontend Docker images build successfully. The recreated stack reports ThreatLens 1.4.0 ready with its database available.
- Live OpenAPI exposes all five filter fields and the filtered count. An unauthenticated filtered import returns HTTP 401.

# Iteration 1.2 — bounded STIX indicator import

Date: 2026-10-25

## Iteration goal

Deliver the smallest useful interoperability path without weakening ThreatLens provenance or claiming untested TAXII support. Analysts can import a local STIX 2.1 JSON bundle, see exactly which objects were accepted, skipped, rejected, newly persisted, or deduplicated, and immediately use the canonical entities in the existing workspace.

## User story and acceptance criteria

As an analyst, I can import an approved STIX bundle so that partner indicators enter the same evidence-aware workflow as connector observations.

- Import requires an analyst or administrator token.
- Bundles are limited to 2 MiB and 500 objects.
- The accepted contract is STIX 2.1 Indicator objects containing one equality comparison for IPv4, IPv6, domain, URL, email, MD5, SHA-1, or SHA-256.
- Every accepted value passes through existing canonical normalization.
- The complete source object is retained as the provider record; producer identity, object markings, labels, confidence, validity, and safe HTTP(S) references remain attached to the observation.
- Unsupported object types are skipped and malformed or out-of-contract indicators are rejected with their object index and reason.
- Valid objects in a partially valid bundle still import.
- Reimporting the same object returns the existing observation ID. A changed raw object receives a different content hash and traceable record.
- Imports emit immutable audit events and never dereference IoCs or supplied references.
- The Intelligence workspace shows file limits, the supported subset, outcome totals, per-object issues, and links imported entities back into search.

## Protocol decision

GOSINT is used as a workflow reference for collection, standardization, filtering, and export. OpenTAXII is used as a TAXII 1.x server reference: its maintained documentation states support for TAXII 1.0 and 1.1. ThreatLens 1.2 does not implement a TAXII client or server, and the manual STIX 2.1 import endpoint must not be described as TAXII compatibility.

## Verification

- 54 backend tests cover the complete Phase 0–8 baseline plus all eight STIX IoC mappings, authorization, bundle limits, contract validation, partial results, provenance, auditing, and idempotency.
- Ruff passes and strict mypy reports no issues across 57 backend source files.
- 11 frontend tests cover the existing shell, theme, dashboard, intelligence requests, and STIX import request contract.
- The Angular production build passes at 349.02 kB initial raw size, below its 500 kB warning budget.
- The production npm dependency audit reports zero vulnerabilities.
- PostgreSQL reports no migration drift, fresh backend and frontend Docker images build successfully, and the recreated stack serves direct and proxied 1.2.0 readiness responses. The proxied source registry and OpenAPI expose the bounded import contract, while an unauthenticated live request returns 401.

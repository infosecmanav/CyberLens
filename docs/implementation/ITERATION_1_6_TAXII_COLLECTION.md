# Iteration 1.6 — bounded TAXII 2.1 collection

Date: 2026-10-25

## Outcome

ThreatLens can collect STIX 2.1 indicators from an administrator-approved TAXII 2.1 relationship without exposing credentials or bypassing the existing import controls. Collection remains read-only. Every page passes through the same normalization, deduplication, quarantine, provenance, and analyst-promotion boundary as a manual STIX import.

## Delivered behavior

- Administrators register a fixed HTTPS discovery URL and an optional backend environment-variable name for a bearer token. Secret values never appear in database configuration, API responses, audit data, or browser state.
- Discovery accepts at most ten API roots and constrains the selected root to the configured HTTPS authority. Credentials, query strings, fragments, and cross-authority roots are rejected.
- Collection discovery records independent `can_read` and `can_write` capabilities. Polling requires an explicitly selected, readable collection on an enabled server.
- Polling retrieves a bounded manifest and at most 20 configured pages of 200 objects each. Opaque TAXII `next` tokens are only sent back to the fixed objects endpoint.
- A successful run advances a durable `added_after` cursor from manifest `date_added` values. Failed runs retain the previous cursor and record a bounded operational error.
- Every page is represented by an import batch from the `taxii-2-1` source. Supported indicators are persisted idempotently; unsupported or invalid objects remain visible as per-object outcomes.
- The scheduler polls due selected collections using the relationship creator as the attributed actor. Manual and scheduled runs use the same service and run ledger.
- The dark/light Settings console shows relationship readiness, credential presence, advertised access, limits, cursors, schedules, and manual poll controls.

## Compatibility boundary

The compatibility claim is TAXII 2.1 media types and endpoints exercised by sanitized fixtures. It does not claim OpenTAXII 2.x support: the reviewed OpenTAXII documentation covers TAXII 1.0 and 1.1. A real partner relationship still requires bounded, opt-in validation against that server's authentication and deployment behavior.

## Verification

- Fixture tests cover discovery, collection metadata, manifest cursor extraction, two-page object delivery, bearer authentication, 401, 403, 429, and cross-authority rejection.
- API tests cover administrator-only configuration, discovery, collection authorization, polling, STIX ledger reuse, source attribution, cursor persistence, and unsafe URL rejection.
- The complete backend regression suite, Ruff, strict mypy, Angular unit suite, production build, PostgreSQL migration upgrade, Docker health checks, and representative API probes are required before release.

## Remaining interoperability work

Automated enrichment and controlled STIX/TAXII export remain separate increments. Export stays disabled until marking checks, destination allowlists, approval records, immutable audit data, and explicit write authorization are implemented and tested.

# Iteration 1.9 — scheduled intelligence feeds and NVD lookup

Date: 2026-10-25

## Outcome

ThreatLens can collect an approved non-TAXII feed on a controlled schedule and retain a per-record processing ledger. CISA KEV is the first feed-capable provider. NVD CVE API 2.0 adds a separate bounded lookup adapter without overstating live deployment validation.

## Delivered behavior

- Administrators can create one subscription per feed-capable catalog source with an explicit cadence and a hard limit of 1–5,000 records per run.
- Subscriptions can be paused, resumed, or run manually. The existing scheduler runs due subscriptions and advances the next-run time after every attempt.
- CISA KEV feed records follow the same canonical CVE normalization, raw-source preservation, content hashing, source health, source-record, and observation boundaries as interactive lookup.
- Repeat collection reuses canonical entities, source records, and observations. Changed provider records produce a new content hash and traceable source record.
- Every accepted, deduplicated, or rejected record is retained in an ordered feed-run ledger with its disposition and lineage links. Collected observations are never promoted to evidence automatically.
- The administrator console presents subscription state, cadence, record budget, next run, manual collection, and recent import, deduplication, and rejection counts in both light and dark themes.
- The NVD connector uses the fixed CVE API 2.0 endpoint, an optional backend-only `NVD_API_KEY`, a single `cveId` query, bounded normalized CVSS/CWE context, full raw provenance, and explicit absent, forbidden, throttled, malformed, and transport outcomes.
- The source matrix labels NVD `ADAPTER_SCAFFOLDED` because fixture verification is complete but bounded live endpoint validation remains pending. CISA KEV remains the only source advertised as public-feed supported.

## Verification

- Connector fixtures cover CISA feed bounds plus NVD success, absence, forbidden access, throttling, parse failure, optional authentication, normalized timestamps, CVSS/CWE context, and provenance.
- API tests cover admin authorization, unsupported sources, subscription creation, collection, durable lineage, repeat-run deduplication, pause behavior, and run history.
- Frontend service tests cover bounded subscription creation, configuration, and manual-run contracts.
- Release checks include the complete backend regression suite, Ruff, strict mypy, Angular tests, production build, production dependency audit, clean PostgreSQL migration replay and parity, Docker health, and live OpenAPI and health responses.

## Trust boundary

Feed sources must be registered connectors with an explicit `fetch_feed` capability. The browser cannot supply arbitrary feed URLs or credentials. Provider absence remains an observation outcome rather than a safety verdict, and collection cannot create analyst evidence or trigger outbound sharing.

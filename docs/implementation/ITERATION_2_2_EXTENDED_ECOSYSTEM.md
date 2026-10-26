# Iteration 2.2 — extended permitted ecosystem

Date: 2026-10-26

ThreatLens 2.2 completes the planned provider expansion with bounded read-only connectors and explicit access boundaries.

## Delivered

- Added authenticated URLhaus host/URL intelligence and MalwareBazaar hash-metadata lookup using the shared `ABUSECH_AUTH_KEY`. Malware samples are never downloaded, executed, or uploaded.
- Added a cached, bounded Feodo Tracker JSON feed with IPv4 normalization and per-record quarantine.
- Added a cached, bounded OpenPhish community text feed with URL normalization, malformed-record quarantine, stable external identifiers, and an analyst-validation warning.
- Generalized scheduled-feed routing so every registered `fetch_feed` capability can use the durable subscription and run ledger.
- Extended the feed console with CISA KEV, Feodo Tracker, and OpenPhish selectors while retaining cadence and record budgets.
- Added API-level acceptance coverage proving that missing VirusTotal credentials and a quota-exhausted source do not discard successful collection results.
- Hardened administrator-configured TAXII discovery URLs against localhost, single-label/internal names, loopback, private, and reserved literal addresses.
- Marked Google Safe Browsing `TERMS_RESTRICTED`; its documented non-commercial boundary is represented without a connector.

## Trust boundaries

- Feed presence and provider reputation remain observations, not automatic evidence or maliciousness verdicts.
- Scheduled records are deduplicated by provider, canonical entity, and raw-content hash while retaining their source record.
- Cross-provider reports remain distinct records even when they resolve to the same canonical entity; this preserves independent provenance and avoids false corroboration.
- OpenPhish URLs are stored and normalized only. ThreatLens never requests a submitted indicator URL.
- URLhaus is lookup-only, urlscan is passive-search-only, and VirusTotal submissions are unavailable.

## Validation

- Ruff and strict mypy passed across 94 backend source files.
- The complete backend suite passed: 122 tests, with one documented upstream Starlette `TestClient` deprecation warning.
- All 22 Angular tests passed. The optimized build produced a 350.33 kB initial bundle with feature routes lazy loaded, and the production dependency audit reported zero vulnerabilities.
- Compose configuration and clean image builds passed. PostgreSQL replayed all ten migrations from an empty database to `20261025_0010`, and Alembic reported no ORM drift.
- Backend, database, and frontend containers became healthy. Direct and frontend-proxied health requests reported version 2.2.0, and the live OpenAPI document exposed representative source, feed, TAXII, lookup, and investigation routes.

Live credential validation remains owner-controlled and is not inferred from fixture success.

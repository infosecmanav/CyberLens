# Phase 2 intelligence collection — milestone 1

Date: 2026-10-22

This milestone turns the Phase 1 connector contract into a usable, persisted intelligence workflow. It is the first Phase 2 increment; the full provider catalogue is still scheduled for later connector waves.

## Implemented behavior

- Canonical normalization and automatic detection for IPv4, IPv6, domains, HTTP(S) URLs, MD5, SHA-1, SHA-256, email addresses, CVEs, and ASNs.
- Explicit normalization for certificates, nameservers, CIDR ranges, products, malware families, campaigns, threat actors, and ATT&CK technique IDs.
- URL handling rejects embedded credentials, removes fragments, normalizes host names, and never sends a request to a submitted IOC URL.
- `CollectionJob` and `SourceRecord` persistence through Alembic revision `20261022_0002`; repeat collection jobs reuse canonical entities, provider records, and normalized observations.
- Intelligence APIs for normalization, lookup, entity listing, entity detail, and persisted observations.
- Connector outcome handling for success, no result, authentication, forbidden access, rate limits, timeouts, network errors, malformed data, and source failures.
- A CISA KEV connector using the official `cisagov/kev-data` JSON dataset with a 15-minute in-process cache.
- An OSV CVE adapter with fixture coverage. It remains conservatively labelled `ADAPTER_SCAFFOLDED` because `api.osv.dev` returned the managed environment's network-policy 403 during live validation.
- Source catalogue synchronization updates verified metadata and capabilities without overwriting runtime health history.
- An Angular Intelligence page that runs the backend workflow and renders persisted source outcomes and observations. Demonstration data is opt-in and visibly labelled.

## API surface

| Method | Route | Behavior |
| --- | --- | --- |
| `POST` | `/api/v1/intelligence/normalize` | Validate and normalize without persistence |
| `POST` | `/api/v1/intelligence/lookup` | Normalize, deduplicate, collect, and persist |
| `GET` | `/api/v1/intelligence/entities` | Filter and paginate canonical entities |
| `GET` | `/api/v1/intelligence/entities/{id}` | Read one canonical entity |
| `GET` | `/api/v1/intelligence/entities/{id}/observations` | Read normalized, source-backed observations |

`NO_RESULT` is displayed as a successful query with no record. It is never treated as evidence that an entity is safe.

## Verification

- Backend: 32 pytest tests passed.
- Static analysis: Ruff and strict mypy passed.
- Frontend: 4 Vitest tests and the Angular production build passed; the production dependency audit reported no vulnerabilities.
- PostgreSQL: migration upgraded to `20261022_0002`; `alembic check` reported no drift.
- Live source: `CVE-2021-44228` returned one normalized CISA KEV observation from the official dataset.

The remaining Starlette test-client deprecation warning originates in the current FastAPI testing compatibility layer and does not affect runtime requests.

## Current limits and next work

- Add the next verified public and credential-ready connector wave, beginning with CVE.org/NVD, MITRE datasets, OTX, and permitted abuse.ch APIs.
- Move shared response caching and rate-limit state to durable storage before multi-instance deployment.
- Protect collection endpoints with the existing JWT/RBAC layer after the Angular sign-in workflow is implemented.
- Add source health-test endpoints and richer source configuration UI.
- Permit and live-validate `api.osv.dev` in the cloud environment before promoting OSV's implementation status.
- Continue Phase 2 extraction, relationship normalization, scheduled feed ingestion, and provenance-aware duplicate lineage.

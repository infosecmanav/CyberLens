# Intelligence interoperability backlog

Date: 2026-10-25

## Epic outcome

Allow analysts to import, refine, and exchange indicator intelligence through modular adapters while preserving ThreatLens provenance, authorization, deduplication, and evidence boundaries. GOSINT informs the collection-and-processing workflow and OpenTAXII informs trusted automated exchange. Neither is currently an implemented ThreatLens integration.

## Slice 1 — research and contract fixtures

As a maintainer, I can evaluate an integration against verified upstream behavior before the product advertises support.

- Verify the current maintenance state, license, official documentation, authentication model, and supported protocol versions for each candidate.
- Record TAXII 1.x and TAXII 2.x/2.1 as distinct capabilities; do not infer support for one generation from the other.
- Add sanitized STIX/TAXII and feed-format fixtures covering valid, empty, malformed, unauthorized, forbidden, rate-limited, paginated, and partially valid responses.
- Define mappings for indicators, observables, relationships, confidence, timestamps, producer identity, markings, and external identifiers.
- Update the source matrix only after the relevant adapter has fixture tests and, where possible, a bounded live verification.

## Slice 2 — modular read-only collection

As an analyst, I can import indicators from an approved feed or collection without losing their origin or flooding the workspace with duplicates.

- Implement adapters behind the existing connector contract and capability router.
- Keep credentials and collection URLs in backend configuration; redact them from responses, logs, and browser storage.
- Normalize supported IoCs through the existing entity pipeline and retain the original provider object as provenance.
- Make pagination, time windows, request budgets, caching, retry limits, and resume behavior explicit and deterministic.
- Re-importing the same provider object remains idempotent while a changed provider object creates traceable lineage.
- Invalid records are quarantined with parse outcomes rather than silently discarded or promoted to evidence.

## Slice 3 — enrichment and filtering

As an analyst, I can reduce feed noise using visible, reproducible criteria.

- Filter by supported observable type, source, time window, marking, confidence, and validation state.
- Store the applied filter definition and counts so an analyst can reproduce an import result.
- Enrichment remains source attributed and does not convert absence into a safety verdict.
- Analyst promotion to evidence stays separate from collection and enrichment.
- Metrics distinguish received, accepted, deduplicated, rejected, quarantined, and promoted records.

## Slice 4 — trusted TAXII exchange

As an administrator, I can configure an authorized TAXII relationship and control what ThreatLens receives or shares.

- Discovery and collection selection require authenticated backend access and least-privilege configuration.
- Collection-level authorization is enforced independently for read and write operations.
- STIX object markings and sharing restrictions survive import and are checked before export.
- Export is disabled by default, requires an explicit allowlist and approval policy, and emits immutable audit events.
- Pagination, manifests, added-after cursors, duplicate delivery, revocation, and partial failures have integration tests.
- Compatibility claims name the tested TAXII generation and server implementation instead of using a generic “TAXII compatible” label.

## Definition of done

Each slice ships as a reviewable vertical increment with migrations, API schemas, UI states, threat-boundary documentation, and regression tests. Ruff, strict mypy, pytest, Angular tests, the production build, PostgreSQL migration parity, Docker health checks, and representative proxy requests must pass. Live interoperability tests remain bounded and opt-in so routine CI neither consumes partner quota nor publishes intelligence.

## Research references supplied for planning

These references are inputs to the backlog and were not independently revalidated during the 1.1 UI iteration.

1. [MISP](https://www.misp-project.org/)
2. [AlienVault / LevelBlue OTX](https://otx.alienvault.com/)
3. [OpenCTI](https://github.com/OpenCTI-Platform/opencti)
4. [Harpoon](https://randhome.io/blog/2018/02/23/harpoon-an-osint-/-threat-intelligence-tool/)
5. [Yeti](https://github.com/yeti-platform/yeti)
6. [GOSINT](https://github.com/ciscocsirt/GOSINT)
7. [OpenTAXII package reference](https://www.kali.org/tools/opentaxii/)

# Intelligence interoperability backlog

Date: 2026-10-25

## Epic outcome

Allow analysts to import, refine, and exchange indicator intelligence through modular adapters while preserving ThreatLens provenance, authorization, deduplication, and evidence boundaries. GOSINT informs the collection-and-processing workflow and OpenTAXII informs trusted automated exchange. Neither is currently an implemented ThreatLens integration.

## Delivery status

Version 1.2 completes the local contract portion of Slice 1 and the first vertical part of Slice 2. It adds authenticated manual STIX 2.1 JSON bundle import for a bounded set of Indicator patterns, sanitized valid and partial fixtures, canonical normalization, raw-object provenance, markings, confidence, audit events, explicit per-object issues, and idempotent persistence. Network TAXII discovery, collection polling, manifests, added-after cursors, and export remain unimplemented.

Version 1.3 adds durable import batches and ordered object outcomes. Analysts can reopen an import report, filter clean and issue-bearing batches, follow accepted objects to canonical records, and review the bounded raw content of rejected or skipped objects. Criteria-based pre-import filtering and network TAXII work remain in the backlog.

Version 1.4 completes the first vertical increment of Slice 3. Optional filters constrain supported observable type, minimum confidence, an inclusive `valid_from` window, and required markings. The canonical definition and filtered count are stored with each batch, and each excluded object remains reviewable without being promoted into evidence. Source selection remains fixed to the manual STIX source; validation failures remain quarantined. Enrichment workflows, promotion state filters, and network TAXII work remain in the backlog.

Version 1.5 completes the analyst-promotion increment of Slice 3. Accepted import outcomes can be promoted into distinct evidence only through an authenticated analyst action that records polarity, claim, uncertainty, reviewer, review time, and an audit event. Batch metrics and history filters distinguish promoted from unreviewed imports.

Version 1.6 completes the read-only collection portion of Slice 4. Administrators configure HTTPS discovery endpoints and optional bearer-token environment names, explicitly authorize readable collections, and control cadence. The tested TAXII 2.1 client supports discovery, collections, manifests, opaque pagination, deterministic page and object budgets, `added_after` cursors, scheduling, durable runs, partial-object quarantine, and STIX import lineage. Automated enrichment and controlled export remain in the backlog.

Version 1.7 completes the automated enrichment portion of Slice 3. Administrators define explicit entity and connector allowlists, cadence, and per-run entity budgets. New canonical entities are processed once per policy through the existing connector contract, with durable collection-job links, per-source outcomes, reused and new observation IDs, and audit events. Demonstration sources are blocked from automation, and `NO_RESULT` creates neither an observation nor a safety verdict. Controlled export remains in the backlog.

Version 1.8 completes the controlled sharing portion of Slice 4. Export policies are created disabled and bind one currently write-authorized TAXII collection to explicit marking rules and an object budget. Only analyst-reviewed evidence backed by STIX 2.1 Indicators can enter a frozen bundle. The payload preserves markings and available marking definitions, records a SHA-256 hash, requires approval by a different administrator, rechecks write authorization at delivery, and stores an immutable audit trail and bounded TAXII receipt.

Version 1.9 completes scheduled non-TAXII feed collection. Administrators can configure one bounded subscription per feed-capable source, control cadence and per-run record budget, pause or run collection, and review durable per-record import, deduplication, and rejection outcomes. CISA KEV supplies the first scheduled feed. A fixture-verified NVD CVE API 2.0 lookup adapter adds provider breadth while retaining a conservative `ADAPTER_SCAFFOLDED` label until bounded live validation is allowed.

Upstream verification on 2026-10-25 found that OpenTAXII documents TAXII 1.0 and 1.1 support and describes the project as feature-complete with bug-fix maintenance. It does not establish TAXII 2.x or 2.1 support. Any future TAXII 2.1 client will therefore use a separately verified implementation and compatibility suite.

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

These references began as planning inputs. GOSINT and the OpenTAXII repository documentation were revalidated for the 1.2 contract iteration on 2026-10-25; the remaining references retain their earlier planning status.

1. [MISP](https://www.misp-project.org/)
2. [AlienVault / LevelBlue OTX](https://otx.alienvault.com/)
3. [OpenCTI](https://github.com/OpenCTI-Platform/opencti)
4. [Harpoon](https://randhome.io/blog/2018/02/23/harpoon-an-osint-/-threat-intelligence-tool/)
5. [Yeti](https://github.com/yeti-platform/yeti)
6. [GOSINT](https://github.com/ciscocsirt/GOSINT)
7. [OpenTAXII package reference](https://www.kali.org/tools/opentaxii/)

# Post-Phase-2 delivery plan

Date: 2026-10-26

This plan maps the master implementation specification to reviewable ThreatLens increments. The work is complete through Wave 10. Provider status remains capability-specific: a source can be inventoried, fixture-tested, awaiting a key, publicly feed-capable, restricted, or still under investigation without being presented as live.

| Wave | Delivered increment | Primary evidence |
| ---: | --- | --- |
| 0 | Repository baseline, gap analysis, and 106-source inventory | `PHASE_0_1_REPORT.md`, `SOURCE_MATRIX.md` |
| 1 | Connector contracts, explicit outcomes, registry, source health, and credential boundary | `PHASE_2_REPORT.md`, `WAVE_1_REPORT.md` |
| 2 | Primary CTI and vulnerability adapters | `ITERATION_2_0_PRIMARY_CTI.md` |
| 3 | Passive infrastructure, registration, certificate, URL, reputation, and phishing collection | `ITERATION_2_1_INFRASTRUCTURE.md`, `ITERATION_2_2_EXTENDED_ECOSYSTEM.md` |
| 4 | Permitted abuse.ch metadata/feed integrations, OpenPhish, STIX ingestion, and TAXII exchange | `ITERATION_2_2_EXTENDED_ECOSYSTEM.md`, `INTELLIGENCE_INTEROPERABILITY_BACKLOG.md` |
| 5 | Evidence-backed investigations and analyst decision history | `PHASE_3_8_REPORT.md` |
| 6 | Evidence-backed graph, temporal relationships, and contextual similarity | `PHASE_3_8_REPORT.md` |
| 7 | Deterministic planning, budgets, cancellation, resumption, and untrusted-text isolation | `PHASE_3_8_REPORT.md` |
| 8 | Evidence-gated Sigma, SPL, and KQL candidates with validation states | `PHASE_3_8_REPORT.md` |
| 9 | Cases, tasks, nine playbooks, approvals, audit, and dry-run actions | `PHASE_3_8_REPORT.md` |
| 10 | Monitoring, security hardening, responsive console, release validation, and source truthfulness | `WAVE_10_REPORT.md` |

## Delivery rules

- Build vertical increments against real persisted APIs and keep demonstration data explicitly labelled.
- Preserve provider records, canonical entities, observations, evidence, markings, and audit lineage as distinct records.
- Treat missing credentials, rate limits, quotas, malformed responses, and unavailable sources as visible outcomes. Other applicable sources continue.
- Keep live provider checks bounded and opt-in. Routine tests use sanitized fixtures and consume no provider quota.
- Keep active scans, sample downloads, sample uploads, URL submissions, and external response execution disabled.
- Require analyst evidence promotion and human approval at the existing trust boundaries.

## Deferred owner-dependent validation

Credential-based connectors remain `IMPLEMENTED_AWAITING_KEY` or conservatively scaffolded until the owner supplies permitted credentials and explicitly runs a bounded source test. Paid-only, unavailable, restricted, and unreviewed providers remain visible in the source matrix with their limitation. These states are expected product behavior and do not block investigations that use other sources.

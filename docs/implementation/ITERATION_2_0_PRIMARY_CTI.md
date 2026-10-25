# Iteration 2.0 — primary CTI connector wave

Date: 2026-10-25

## Outcome

ThreatLens implements the master plan's primary read-only CTI lookup wave behind the existing capability router. Missing credentials remain isolated `NOT_CONFIGURED` outcomes, provider responses retain raw provenance, and the source registry distinguishes fixture verification from successful live authentication.

## Delivered connectors

- **VirusTotal API v3:** IPv4, IPv6, domain, URL, and file-hash lookup with URL-safe identifiers, analysis counts, reputation context, timestamps, and explicit public-tier restrictions. Submissions are disabled.
- **LevelBlue OTX:** indicator general-context lookup for network indicators, hashes, and CVEs, including pulse count and latest pulse provenance.
- **ThreatFox:** bounded IOC search through the shared abuse.ch authentication key, with malware, threat type, confidence, tags, and first/last-seen context.
- **MISP:** bounded attribute lookup against an administrator-configured HTTPS server. Credentials stay in backend environment variables, redirects are disabled, and localhost or private/reserved IP destinations are rejected.
- **CVE.org:** public published CVE record lookup with CNA description, affected products, state, assigner, and publication/update timestamps.
- **MITRE ATT&CK Enterprise:** cached lookup of official STIX attack-pattern objects by technique or sub-technique ID, with platform, kill-chain, revoked, and deprecated context.

These join the existing CISA KEV, NVD, and OSV vulnerability connectors. All results flow through canonical entities, collection jobs, source records, observations, deduplication, and source health.

## Source health workflow

- `GET /api/v1/sources/{source_id}/health` reports persisted health, last checks, required credential names, and which names are configured. It never returns values.
- `POST /api/v1/sources/{source_id}/test` requires an administrator and a typed canonical value. It makes one explicit provider lookup, updates source health, emits an audit event, and does not persist returned intelligence.
- The Source Registry provides the same bounded check for signed-in administrators and warns that it may consume one provider request.

## Verification

- Fixture tests cover success, absence, missing credentials, rate limits, malformed payloads, authentication headers, provider-specific normalization, caching, provenance, and private MISP destination rejection.
- API tests cover source inventory truthfulness, public health visibility, administrator-only testing, `NOT_CONFIGURED`, and healthy local-fixture outcomes.
- Frontend tests cover full registry loading and the typed source-test request contract.
- Full release gates include Ruff, strict mypy, pytest, Angular tests/build, production dependency audit, Docker, PostgreSQL migration parity, and representative proxied requests.

## Remaining provider work

The next controlled wave covers permitted infrastructure, exposure, DNS, URL, and reputation lookups. Sources without verified automated access remain visible as `INVESTIGATION_NEEDED`, restricted, paid, or manual rather than being presented as working integrations.

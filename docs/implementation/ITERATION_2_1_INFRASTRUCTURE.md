# Iteration 2.1 — infrastructure, registration, URL, and reputation

Date: 2026-10-25

## Outcome

ThreatLens implements the master plan's bounded infrastructure and passive context wave. Every adapter is read-only, advertises only supported entity types, preserves raw provider data and timestamps, and keeps reputation, exposure, registration, certificate, and historical scan context separate from maliciousness or attribution.

## Delivered connectors

- **Shodan:** minified host-information lookup for IPv4 and IPv6. It retains observed ports, hostnames, domains, ASN, organization, country code, and provider timestamp. Active scanning is disabled.
- **Censys:** bearer-authenticated platform host lookup for IPv4 and IPv6 with bounded service, DNS, location, and autonomous-system context. Search automation and scanning are disabled.
- **GreyNoise:** community IPv4 context with noise, RIOT, classification, scanner name, and last-seen fields. The observation explicitly describes scanner context rather than a maliciousness verdict.
- **AbuseIPDB:** bounded 90-day IP check with community-report counts and confidence context. The UI and observation summary require analyst interpretation.
- **RDAP:** public domain and IP registration lookup through the fixed RDAP bootstrap service, retaining status, range, nameserver, and event context.
- **crt.sh:** passive certificate-transparency lookup with a deterministic 100-record provenance bound and distinct total/truncated counts.
- **urlscan.io:** passive historical search for domain, URL, and IP entities with a 20-result bound. The connector performs only `GET` requests; URL submission and scan visibility actions are disabled.

## Access truthfulness

Shodan, Censys, GreyNoise, and AbuseIPDB remain `IMPLEMENTED_AWAITING_KEY` until an owner-supplied credential passes an explicit bounded test. RDAP, crt.sh, and urlscan.io remain `ADAPTER_SCAFFOLDED` pending bounded live validation in the deployment network. Provider plan, quota, commercial-use, and attribution limits appear in the registry and generated source matrix.

## Verification

- Fixture tests cover missing credentials, authentication placement, success normalization, timestamps, provenance, bounds, passive-only HTTP methods, empty results, and interpretation boundaries.
- The complete backend suite, Ruff, strict mypy, Angular suite, production build, production dependency audit, Docker health, Alembic parity, and live health/OpenAPI checks remain release gates.

## Security boundary

Submitted indicators are encoded only into fixed provider endpoints. The system never browses a submitted URL, performs a port scan, submits a URL to urlscan.io, or interprets geography or registration data as actor identity. Paid endpoints and active capabilities remain outside the implemented boundary.

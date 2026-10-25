# Testing strategy

## Required checks

- Backend pytest runs against an isolated SQLite database and covers health, authentication, RBAC, source inventory, connector routing, normalization, deduplication, investigation execution, budget exhaustion, resume/idempotency, prompt-injection resistance, graph evidence, detection validation, approvals, dry runs, playbooks, monitoring baselines, duplicate suppression, and audit metrics.
- Ruff and strict mypy validate every backend source module.
- Alembic upgrades a real PostgreSQL database and `alembic check` verifies ORM/migration parity.
- Angular tests use Vitest with jsdom. Shell tests cover route rendering, command-palette keyboard access, and theme changes; service tests cover persisted theme behavior and intelligence requests. The production build checks strict templates, TypeScript, styles, route chunks, and bundle budgets.
- Docker Compose must build all application images, reach healthy status, and satisfy representative API and frontend-proxy requests.

## Provider testing

Automated tests do not consume provider quota. Connector tests use sanitized fixtures for success, empty results, malformed data, authentication failures, forbidden requests, rate limits, quota exhaustion, timeouts, and network failures. Live checks are bounded, opt-in, and promote a source only after the current environment verifies its documented endpoint and access terms.

`NO_RESULT` means the provider completed the query without a matching record. It never means an entity is safe. Demonstration records are explicitly labelled and counted separately in operational metrics.

## Safety and integrity cases

Tests assert that objective prompt-injection text cannot alter the deterministic plan; a zero request budget waits for an analyst; repeat runs reuse completed steps and collection jobs; high-impact tasks cannot execute before approval; completed actions remain dry-run; production detection validation requires recorded evidence; and graph output carries its attribution limitation.

The current Starlette `TestClient` emits one upstream deprecation warning about its `httpx` compatibility layer. It does not change request behavior or runtime dependencies.

The Angular 20 test builder currently constrains Vitest to version 3. The full development-tool audit therefore reports upstream Vitest and worker-pool advisories whose patched releases require a coordinated Angular/Vitest major upgrade. The production dependency audit is clean. Until that upgrade is tested, run the development server and test runner only in a trusted local environment and never expose them as a production service.

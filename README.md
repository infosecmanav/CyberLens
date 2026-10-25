# ThreatLens

ThreatLens is an evidence-backed cyber-threat intelligence and investigation platform. Version 1.1 builds on the complete Phase 0–8 baseline with an enterprise analyst console, persistent dark mode, keyboard navigation, and real-metric operational posture graphics.

## What works

- FastAPI, PostgreSQL, Alembic, JWT authentication, Argon2 password hashing, and analyst/admin roles.
- A registry of 105 intelligence sources with explicit implementation and health states.
- Canonical entity normalization, deduplicated collection, provider records, observations, and evidence.
- A verified read-only CISA KEV public-feed connector, fixture-tested OSV adapter, and labelled local demonstration source.
- Deterministic five-step investigation plans with request, runtime, entity, graph, report, and zero-cost budgets.
- Resumable and idempotent investigation execution, immutable analyst decisions, evidence-backed findings, and separate confidence dimensions.
- Bounded relationship graphs and contextual similarity with an explicit attribution limitation.
- Evidence-gated Sigma, SPL, and KQL candidates with test and production validation states.
- Cases, tasks, immutable audit events, nine seeded playbooks, approval gates, and dry-run-only response execution.
- Scheduled monitoring objectives that distinguish baselines, duplicate results, and actionable material changes.
- A responsive Angular workspace for every phase, including Cytoscape graph exploration.
- A light/dark theme that follows the initial system preference, persists analyst choice, and keeps graph rendering theme-aware.
- A `Ctrl/⌘ K` command palette and a security-console dashboard whose charts use observed API metrics rather than invented trends.

The CISA KEV catalogue is the only remote source currently marked as public-feed supported. OSV remains `ADAPTER_SCAFFOLDED` until its live endpoint is allowed and validated. Other catalogue entries stay conservative until their access and connector behavior are verified. Demonstration evidence is opt-in and remains labelled throughout the system.

## Run with Docker Compose

```bash
cp .env.example .env
# Set APP_SECRET_KEY in .env to a long random value.
docker compose up --build
```

Open the Angular app at `http://localhost:4200`, the API at `http://localhost:8000`, and the OpenAPI documentation at `http://localhost:8000/api/docs`. The PostgreSQL credentials in `compose.yaml` are for local development only.

The first registered account becomes the workspace administrator. Later accounts receive the analyst role. Tokens are kept in browser memory and are cleared by refresh or sign-out.

## Run locally

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 24+, npm 11+, Docker, and Docker Compose.

```bash
cd backend && uv sync --extra dev --frozen && cd ..
cd frontend && npm ci && cd ..
docker compose up -d db
cd backend
DATABASE_URL=postgresql+asyncpg://threatlens:threatlens@localhost:5432/threatlens uv run alembic upgrade head
DATABASE_URL=postgresql+asyncpg://threatlens:threatlens@localhost:5432/threatlens APP_SECRET_KEY=local-development-secret uv run uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm start
```

The Angular development server proxies `/api` to FastAPI.

## Validate

```bash
cd backend
uv run --extra dev ruff check .
uv run --extra dev mypy app
uv run --extra dev pytest -q
DATABASE_URL=postgresql+asyncpg://threatlens:threatlens@localhost:5432/threatlens uv run alembic check
cd ../frontend
npm test -- --watch=false
npm run build
cd ..
docker compose config --quiet
```

## Repository structure

```text
backend/                  FastAPI, SQLAlchemy, Alembic, connectors, engines, and tests
frontend/                 Angular analyst application
docs/implementation/      Architecture, data model, testing, and phase reports
docs/SOURCE_MATRIX.md      Truthful provider inventory
compose.yaml              PostgreSQL and development services
.env.example              Non-secret configuration and credential checklist
```

See the [1.1 UI iteration report](docs/implementation/ITERATION_1_1_SECURITY_CONSOLE.md), [intelligence interoperability backlog](docs/implementation/INTELLIGENCE_INTEROPERABILITY_BACKLOG.md), [Phase 3–8 report](docs/implementation/PHASE_3_8_REPORT.md), [architecture](docs/implementation/ARCHITECTURE.md), [data model](docs/implementation/DATA_MODEL.md), [testing strategy](docs/implementation/TESTING_STRATEGY.md), and [source matrix](docs/SOURCE_MATRIX.md).

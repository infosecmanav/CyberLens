# ThreatLens

ThreatLens is an evidence-backed cyber-threat intelligence and investigation platform. This repository is a greenfield implementation: Phase 0 (project setup) and Phase 1 (foundation) are complete, and the first Phase 2 intelligence-collection milestone is operational.

## What works now

- FastAPI API with liveness/readiness checks and generated OpenAPI documentation
- PostgreSQL persistence with an Alembic migration checked against SQLAlchemy metadata
- JWT authentication with Argon2 password hashing and analyst roles
- Core provenance model: sources, entities, observations, evidence, and relationships
- Capability-aware connector interface, manager, explicit outcomes, timeouts, and bounded concurrency
- Registry of 105 internal and industry sources with truthful implementation and health states
- Local development fixture connector clearly labelled as demonstration-only
- Canonical normalization for IPs, domains, URLs, hashes, email, CVEs, ASNs, certificates, network ranges, ATT&CK techniques, and named entities
- Deduplicated entities, provider source records, observations, and persisted collection jobs
- Read-only CISA KEV connector backed by the official public JSON dataset, with a live feed check
- Fixture-tested OSV adapter with explicit network and provider error outcomes
- Responsive Angular analyst shell, Intelligence search, persisted observation view, dashboard, and Source Registry
- Docker Compose development environment and local Python/Node workflows
- Backend and frontend automated tests

The CISA KEV catalogue is the only remote source currently marked as public-feed supported. OSV remains `ADAPTER_SCAFFOLDED` until its live endpoint is allowed and validated in the managed environment. All other provider rows remain conservative inventory entries.

## Run with Docker Compose

```bash
cp .env.example .env
# Set APP_SECRET_KEY in .env to a long random value.
docker compose up --build
```

Open the Angular app at `http://localhost:4200`, the API at `http://localhost:8000`, and API documentation at `http://localhost:8000/api/docs`.

The default PostgreSQL credentials in `compose.yaml` are for local development only.

## Run services locally

Requirements: Python 3.12+, Node.js 24+, npm 11+, Docker, and Docker Compose.

```bash
make install
docker compose up -d db
cd backend
DATABASE_URL=postgresql+asyncpg://threatlens:threatlens@localhost:5432/threatlens ../.venv/bin/alembic upgrade head
DATABASE_URL=postgresql+asyncpg://threatlens:threatlens@localhost:5432/threatlens APP_SECRET_KEY=local-development-secret ../.venv/bin/uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm start
```

The Angular development server proxies `/api` to FastAPI on port 8000.

## Validate

```bash
.venv/bin/ruff check backend
.venv/bin/pytest backend -q
cd frontend && npm test -- --watch=false
cd frontend && npm run build
docker compose config --quiet
```

With PostgreSQL running, verify migration drift:

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://threatlens:threatlens@localhost:5432/threatlens ../.venv/bin/alembic check
```

## Repository structure

```text
backend/                  FastAPI, SQLAlchemy, Alembic, connectors, tests
frontend/                 Angular analyst application
docs/implementation/      Architecture, data model, tests, and phase report
compose.yaml              PostgreSQL and application development services
.env.example              Non-secret configuration and credential checklist
```

See [Phase 0–1 report](docs/implementation/PHASE_0_1_REPORT.md), [Phase 2 milestone report](docs/implementation/PHASE_2_REPORT.md), [architecture](docs/implementation/ARCHITECTURE.md), [data model](docs/implementation/DATA_MODEL.md), and [source matrix](docs/SOURCE_MATRIX.md).

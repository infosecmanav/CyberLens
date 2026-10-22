# Testing strategy

## Current checks

- Backend API tests run against isolated SQLite databases and cover health, registration, login, authorization, source inventory, source details, connector routing, labelled fixtures, and timeouts.
- Alembic is upgraded against PostgreSQL and `alembic check` confirms that the migration matches ORM metadata.
- Angular component tests use Vitest with jsdom and verify the application shell and navigation.
- The Angular production build verifies templates, TypeScript, styles, and bundle budgets.
- A functional startup check requests FastAPI directly and through Angular's development proxy.

## Connector test rule

Unit tests never call provider services or consume quota. Phase 2 connectors will use captured, sanitized fixtures for success, empty results, malformed responses, authentication failures, forbidden requests, rate limits, quota exhaustion, timeouts, and schema changes. Live tests will be separately marked, bounded, and opt-in after credentials are provided.

## Required future scenarios

The master specification's evidence conflict, deduplication, source outage, SSRF protection, budget enforcement, prompt injection resistance, analyst verdict, and detection-validation cases remain future phase requirements. Passing foundation tests does not claim those workflows exist.


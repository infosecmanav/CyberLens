.PHONY: install test lint migrate dev down

install:
	cd backend && uv sync --extra dev --frozen
	cd frontend && npm ci

test:
	cd backend && uv run --extra dev pytest -q
	cd frontend && npm test -- --watch=false

lint:
	cd backend && uv run --extra dev ruff check .
	cd backend && uv run --extra dev mypy app
	cd frontend && npm run build

migrate:
	cd backend && uv run alembic upgrade head

dev:
	docker compose up --build

down:
	docker compose down


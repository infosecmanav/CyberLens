.PHONY: install test lint migrate dev down

install:
	python3 -m venv .venv
	.venv/bin/pip install -e './backend[dev]'
	cd frontend && npm ci

test:
	.venv/bin/pytest backend
	cd frontend && npm test -- --watch=false

lint:
	.venv/bin/ruff check backend
	cd frontend && npm run build

migrate:
	cd backend && ../.venv/bin/alembic upgrade head

dev:
	docker compose up --build

down:
	docker compose down


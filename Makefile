.PHONY: dev up down lint test build schema

dev:
	docker compose up --build

up:
	docker compose up -d --build

down:
	docker compose down

lint:
	cd backend && uv run ruff check . && uv run mypy src
	npm run lint

test:
	cd backend && uv run pytest
	npm run relay
	npm run test:web

build:
	docker compose build

schema:
	cd backend && uv run python -m reviewer.schema_export ../packages/graphql/schema.graphql
	npm run relay

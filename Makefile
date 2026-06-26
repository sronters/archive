SHELL := /bin/sh

.PHONY: up down logs backend-check frontend-check check test migrate

up:
	docker compose up --build

down:
	docker compose down --remove-orphans

logs:
	docker compose logs -f

backend-check:
	python -m pytest tests

frontend-check:
	pnpm --dir apps/admin-web lint
	pnpm --dir apps/admin-web typecheck

check: backend-check frontend-check

test: backend-check

migrate:
	alembic upgrade head

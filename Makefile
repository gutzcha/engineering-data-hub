# ===
# File Summary
# Path: Makefile
# Type: shell
# Purpose: Developer task runner for build, test, migration, and workflow commands.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: file-level implementation
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

dev:
	docker compose -f compose.yaml -f compose.dev.yaml up --build

test:
	docker compose -f compose.yaml -f compose.dev.yaml run --rm backend pytest

frontend-test:
	docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run

lint:
	docker compose -f compose.yaml -f compose.dev.yaml run --rm backend ruff check .

migrate:
	docker compose -f compose.yaml -f compose.dev.yaml run --rm backend python manage.py migrate


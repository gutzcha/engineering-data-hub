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

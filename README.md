# Plastic Engineering Data Hub

Plastic Engineering Data Hub is a self-contained local-server application for managing engineering data, files, search, and operational workflows for plastic engineering teams. It is designed to run behind a company VPN with internal HTTPS and without requiring host-level Python, Node, PostgreSQL, Redis, or search service installs.

## Runtime Services

- `proxy`: Caddy reverse proxy with internal TLS.
- `backend`: Django API and admin application.
- `worker`: Celery background worker.
- `beat`: Celery scheduler.
- `db`: PostgreSQL database.
- `redis`: Redis broker and cache.
- `meilisearch`: Full-text search service.
- `frontend`: React/Vite frontend application.

## Quickstart

The Compose stack loads `.env.example` by default so config validation and first-run development startup work before a local `.env` exists. These are non-production defaults only.

For production deployment, copy `.env.example` to `.env` and replace all placeholder secrets, passwords, hostnames, and email values before starting the stack:

```bash
cp .env.example .env
```

Start the local development stack:

```bash
make dev
```

The development override exposes:

- Caddy proxy: `https://plastic-hub.local`
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Meilisearch: `http://localhost:7700`

PostgreSQL is intentionally kept on the internal Docker network by default.

## Verification

Run the backend and frontend test suites through Compose:

```bash
make test
make frontend-test
```

Run the focused backend traceability acceptance flow:

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps -e DJANGO_SETTINGS_MODULE=plastic_hub.settings.test backend pytest tests/e2e/test_traceability_flow.py
```

Run the Playwright traceability flow against the Caddy/proxy origin after the local stack is up:

```bash
npx playwright test frontend/e2e/traceability.spec.ts
```

The Playwright test defaults to `https://plastic-hub.local` and can be pointed elsewhere with `PLAYWRIGHT_BASE_URL`. If Meilisearch is not exposed on `http://localhost:7700`, set `PLAYWRIGHT_MEILI_URL`.

## Release Package

Use [docs/release-checklist.md](docs/release-checklist.md) before pilot cutover or production release. It covers Compose build/start, migrations, starter configuration publish, admin user setup, writable backups, HTTPS certificate mounting, health checks, Meilisearch indexing, and the traceability acceptance flow.

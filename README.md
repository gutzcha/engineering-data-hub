<!--
===
File Summary
Path: README.md
Type: markdown
Purpose: Project-level entrypoint with setup, architecture summary, and contributor orientation.
Primary responsibilities:
- Domain behavior is summarized for fast onboarding and avoids full-file reread.
- Core symbols: Plastic Engineering Data Hub
Inputs:
- Downstream and upstream interactions in the same domain.
Outputs:
- API payloads, records, side effects, or UI views depending on file role.
Dependencies:
- Shared runtime services and adjacent domain modules.
Known risks:
- Validate behavior after migrations, dependency upgrades, or contract changes.
===

-->

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

## Manuals

- [Human User Manual](docs/manual/user-manual.md): Installation, deployment, startup, and browser workflows for operators, engineers, quality reviewers, project owners, and administrators.
- [Agent Manual](docs/manual/agent-manual.md): Deployment runbooks, maintenance, verification, environment, and handoff rules for AI agents and technical maintainers.

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

Run the Playwright traceability flow from the frontend package after the local stack is up. Playwright is installed under `frontend`, not at the repo root:

```bash
cd frontend
E2E_USERNAME=<test-user> E2E_PASSWORD=<test-password> npx playwright test e2e/traceability.spec.ts
```

The Playwright test defaults to `https://plastic-hub.local` and can be pointed elsewhere with `PLAYWRIGHT_BASE_URL`. If Meilisearch is not exposed on `http://localhost:7700`, set `PLAYWRIGHT_MEILI_URL`. The account must be pre-provisioned with System Admin or equivalent permissions unless you are running against a local development host and explicitly opt into creating/updating the provided test account with `ALLOW_E2E_USER_SEEDING=true`.

Host-run browser prerequisites:

- Frontend dependencies installed with `npm install` or `npm ci`.
- Playwright browser binaries installed with `npx playwright install`.
- Caddy/proxy, backend, frontend, and Meilisearch running and reachable from the host.

## Release Package

Use [docs/release-checklist.md](docs/release-checklist.md) before pilot cutover or production release. It covers Compose build/start, migrations, starter configuration publish, admin user setup, writable backups, HTTPS certificate mounting, health checks, Meilisearch indexing, and the traceability acceptance flow.


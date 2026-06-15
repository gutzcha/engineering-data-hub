# Engineering Data Hub Agent Runbook

This file is the canonical first-read document for agents and technical maintainers working on Engineering Data Hub.

Read this file before touching code, starting services, running seed commands, or claiming the app is ready.

## 1. Product Summary

Engineering Data Hub is a self-hosted engineering data management platform for traceable records, controlled documents, workflow tasks, full-text search, configurable dashboards, imports, audit history, and operational runbooks.

The current reference configuration is for a plastic engineering organization, but the application is intended as a general-purpose engineering/operations data hub. The plastics object types and documents are example domain configuration and demo data, not the architectural limit of the product.

Core promise:

- Structured records with configurable object templates.
- Linked controlled documents and revisions.
- Search URLs that preserve exact filters.
- Projects, tasks, workflows, and dashboards that navigate to real records.
- Audit-ready operational history.
- Self-contained Docker Compose deployment.

## 2. Repository Identity

- GitHub repository: `https://github.com/gutzcha/engineering-data-hub.git`
- Default branch: `master`
- Local historical workspace name may still be `plastic-engineering-data-hub`.
- License: MIT, see `LICENSE`.

## 3. Critical Rule About Data

The populated database is not stored in Git.

Tracked files include code, migrations, seed commands, starter configuration, docs, tests, and manual screenshots. They do not include live PostgreSQL tables, Docker volumes, uploaded runtime media, backup archives, SQL dumps, or `.env` secrets.

To recreate the local/staging demo dataset, run migrations and then the seed/preparation command described in this runbook.

Never run destructive demo reset commands against production client data.

## 4. Top-Level Path Map

| Path | Purpose |
| --- | --- |
| `README.md` | Public project overview, quickstart, manuals, verification, and license links. |
| `agent.md` | This agent onboarding and operations runbook. |
| `LICENSE` | MIT license. |
| `.env.example` | Safe environment template with placeholders. |
| `example.env` | Safe example environment contract. |
| `.gitignore` | Ignores local secrets, generated assets, reports, backups, and dependency folders. |
| `compose.yaml` | Base Docker Compose service graph. |
| `compose.dev.yaml` | Local development override with host ports. |
| `Makefile` | Convenience commands for dev/test/migrate/lint. |
| `backend/` | Django API, business logic, Celery tasks, tests, and management commands. |
| `frontend/` | React/Vite app, feature modules, unit tests, and Playwright specs. |
| `docs/` | Public product/admin/operations/release/manual documentation. |
| `ops/` | Deployment scripts, Caddy config, backup/restore scripts, and install notes. |

## 5. Backend Path Map

| Path | Purpose |
| --- | --- |
| `backend/manage.py` | Django management entrypoint. |
| `backend/plastic_hub/settings/base.py` | Shared Django settings. |
| `backend/plastic_hub/settings/dev.py` | Development settings. |
| `backend/plastic_hub/settings/prod.py` | Production settings and stricter config validation. |
| `backend/plastic_hub/settings/test.py` | Test settings. |
| `backend/plastic_hub/urls.py` | Top-level API URL routing. |
| `backend/plastic_hub/celery.py` | Celery app bootstrap. |
| `backend/apps/accounts/` | Users, roles, permissions, and account APIs. |
| `backend/apps/api/` | Health and API utility endpoints plus demo seed command. |
| `backend/apps/audit/` | Audit models, middleware, services, and audit APIs. |
| `backend/apps/backups/` | Backup models, services, scheduled tasks, and APIs. |
| `backend/apps/config_registry/` | Configurable object templates, forms, workflows, dashboards, and starter fixtures. |
| `backend/apps/documents/` | Document registry, revisions, storage, extraction, document seed/prep commands. |
| `backend/apps/folders/` | Managed folder templates, scanner, folder events, and review inbox support. |
| `backend/apps/imports/` | File import parsing, mapping, validation, and import execution. |
| `backend/apps/projects/` | Project records, boards, milestones, task dependencies, workload APIs. |
| `backend/apps/records/` | Core dynamic records, versions, validation, codes, serializers, views. |
| `backend/apps/relationships/` | Relationship models, serializers, services, graph APIs. |
| `backend/apps/reports/` | Dashboard/report queries and saved views. |
| `backend/apps/search/` | Meilisearch client, indexers, async indexing tasks, search APIs. |
| `backend/apps/workflows/` | Workflow definitions, engine, tasks, task inbox APIs. |
| `backend/scripts/client_readiness_smoke.py` | Dataset readiness smoke check. |
| `backend/tests/` | Backend unit/integration/e2e tests. |

## 6. Frontend Path Map

| Path | Purpose |
| --- | --- |
| `frontend/package.json` | Frontend scripts and dependencies. |
| `frontend/vite.config.ts` | Vite/Vitest config. |
| `frontend/playwright.config.ts` | Playwright config. |
| `frontend/src/main.tsx` | React entrypoint. |
| `frontend/src/app/App.tsx` | App shell. |
| `frontend/src/app/routes.tsx` | Route definitions. |
| `frontend/src/components/` | Shared UI components. |
| `frontend/src/features/admin-config/` | Admin configuration workspace. |
| `frontend/src/features/audit/` | Audit timeline UI. |
| `frontend/src/features/auth/` | Login/session UI. |
| `frontend/src/features/dashboards/` | Dashboard widgets and saved views. |
| `frontend/src/features/documents/` | Document library/panel/upload/revision UI. |
| `frontend/src/features/folders/` | Folder review inbox and folder panels. |
| `frontend/src/features/imports/` | Import wizard UI. |
| `frontend/src/features/projects/` | Project list/detail/board/timeline/workload UI. |
| `frontend/src/features/records/` | Dynamic record forms, record list/detail, entity graph. |
| `frontend/src/features/search/` | Search page, URL/query filter helpers, filter schema. |
| `frontend/src/features/workflows/` | Task inbox and workflow panels. |
| `frontend/src/lib/api.ts` | Central API client. |
| `frontend/e2e/` | Playwright E2E tests and QA support helpers. |

## 7. Documentation Path Map

| Path | Purpose |
| --- | --- |
| `docs/admin-guide.md` | Admin roles, configuration, workflows, dashboards, templates, safety. |
| `docs/operations-guide.md` | Install, environment, HTTPS, backup/restore, update, health checks. |
| `docs/pilot-rollout.md` | Pilot rollout guidance. |
| `docs/release-checklist.md` | Release and production readiness checklist. |
| `docs/manual/README.md` | Manual package landing page. |
| `docs/manual/user-manual.md` | Human user/operator manual with screenshots. |
| `docs/manual/agent-manual.md` | Agent and technical operator manual. |
| `docs/manual/assets/screenshots/` | Authenticated screenshots of major app pages. |

Internal planning artifacts should not be committed under `docs/`. Keep the repository documentation product-facing unless a maintainer explicitly requests internal notes.

## 8. Runtime Services

Docker Compose services:

| Service | Purpose |
| --- | --- |
| `proxy` | Caddy reverse proxy, HTTPS entrypoint. |
| `frontend` | React/Vite browser app. |
| `backend` | Django REST API. |
| `worker` | Celery worker. |
| `beat` | Celery scheduler. |
| `db` | PostgreSQL. |
| `redis` | Redis broker/cache. |
| `meilisearch` | Full-text search engine. |

Default development ports from `compose.dev.yaml`:

| Surface | URL |
| --- | --- |
| Frontend | `http://127.0.0.1:5173/` |
| Backend | `http://127.0.0.1:8000/` |
| Meilisearch | `http://127.0.0.1:7700/` |
| Caddy HTTPS | `https://plastic-hub.local/` |

## 9. Environment And Secrets

Rules:

- Never commit `.env`.
- Never commit real passwords, tokens, API keys, private certs, production hostnames, or production database dumps.
- `.env.example` and `example.env` must contain placeholders or safe examples only.
- `prepare_client_demo` requires `RELEASE_ADMIN_PASSWORD` in `.env` or the environment.
- Any known local demo password is for local/staging only and must not be used for production.

Fresh local `.env`:

```sh
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

For isolated local verification, set a local-only value:

```env
RELEASE_ADMIN_PASSWORD=LocalOnlyReleaseAdmin!2026
```

Use that value to sign in as `operations_admin` after running `prepare_client_demo`.

## 10. Normal Local Setup

Use this when no other copy of the app is already using the default ports:

```sh
git clone https://github.com/gutzcha/engineering-data-hub.git
cd engineering-data-hub
cp .env.example .env
```

Edit `.env`, set `RELEASE_ADMIN_PASSWORD`, then run:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py migrate
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py prepare_client_demo --confirm-destructive-reset
docker compose -f compose.yaml -f compose.dev.yaml exec backend python scripts/client_readiness_smoke.py
```

Expected smoke output:

```text
Client-readiness smoke: PASS
```

Open:

```text
http://127.0.0.1:5173/
```

Login:

```text
username: operations_admin
password: value of RELEASE_ADMIN_PASSWORD in .env
```

## 11. Isolated Local Setup When Another Stack Is Running

Use this when the default ports `443`, `8000`, `5173`, or `7700` are already occupied by another clone.

Clone into a separate folder:

```sh
git clone https://github.com/gutzcha/engineering-data-hub.git engineering-data-hub-isolated
cd engineering-data-hub-isolated
cp .env.example .env
```

Edit `.env` and set:

```env
APP_HOST=engineering-data-hub.local
RELEASE_ADMIN_PASSWORD=LocalOnlyReleaseAdmin!2026
```

Create an untracked isolated override file named `compose.isolated.yaml`:

```yaml
services:
  proxy:
    ports: !override
      - "4443:443"
  backend:
    ports: !override
      - "8010:8000"
  meilisearch:
    ports: !override
      - "7710:7700"
  frontend:
    ports: !override
      - "5183:5173"
```

Start the isolated stack with a unique Compose project name:

```sh
docker compose -p engineering_data_hub_isolated -f compose.yaml -f compose.dev.yaml -f compose.isolated.yaml up -d --build
docker compose -p engineering_data_hub_isolated -f compose.yaml -f compose.dev.yaml -f compose.isolated.yaml exec backend python manage.py migrate
docker compose -p engineering_data_hub_isolated -f compose.yaml -f compose.dev.yaml -f compose.isolated.yaml exec backend python manage.py prepare_client_demo --confirm-destructive-reset
docker compose -p engineering_data_hub_isolated -f compose.yaml -f compose.dev.yaml -f compose.isolated.yaml exec backend python scripts/client_readiness_smoke.py
```

Open:

```text
http://127.0.0.1:5183/
```

Login:

```text
username: operations_admin
password: LocalOnlyReleaseAdmin!2026
```

When finished, stop the isolated stack:

```sh
docker compose -p engineering_data_hub_isolated -f compose.yaml -f compose.dev.yaml -f compose.isolated.yaml down
```

Add `--volumes` only when intentionally deleting the isolated database and uploaded demo media:

```sh
docker compose -p engineering_data_hub_isolated -f compose.yaml -f compose.dev.yaml -f compose.isolated.yaml down --volumes
```

## 12. Demo Data Recreation Contract

The local/staging dataset is recreated by commands, not by committed SQL dumps.

Tracked recreation files:

| File | Purpose |
| --- | --- |
| `backend/apps/config_registry/fixtures/plastic_engineering_v1.json` | Starter object templates, forms, workflows, dashboards, layouts. |
| `backend/apps/api/management/commands/seed_client_readiness_demo.py` | Client-readiness records and operating data. |
| `backend/apps/documents/management/commands/seed_demo_documents.py` | Demo documents and document revisions. |
| `backend/apps/documents/management/commands/prepare_client_demo.py` | Full local/staging release dataset preparation and search reindex. |
| `backend/scripts/client_readiness_smoke.py` | Readiness smoke check for users, project records, documents, links. |

Required command:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py prepare_client_demo --confirm-destructive-reset
```

For isolated stack:

```sh
docker compose -p engineering_data_hub_isolated -f compose.yaml -f compose.dev.yaml -f compose.isolated.yaml exec backend python manage.py prepare_client_demo --confirm-destructive-reset
```

Expected seeded state:

- Required local users exist.
- `operations_admin` can log in.
- At least 3 project records exist.
- Records cover products, raw materials, specs, suppliers, customers, projects, test methods, and documents.
- Documents are linked to relevant records.
- Search indexes records, documents, folder events, and projects.
- Workflow tasks are openable.
- Admin configuration has published versions/layouts.

## 13. Verification Matrix

Backend import/settings check:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py check
```

Dataset readiness:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec backend python scripts/client_readiness_smoke.py
```

Frontend build:

```sh
cd frontend
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
```

Backend traceability flow:

```sh
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps -e DJANGO_SETTINGS_MODULE=plastic_hub.settings.test backend pytest tests/e2e/test_traceability_flow.py
```

Playwright traceability flow:

```sh
cd frontend
E2E_USERNAME=operations_admin E2E_PASSWORD=<RELEASE_ADMIN_PASSWORD> PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173 npx playwright test e2e/traceability.spec.ts
```

For isolated stack, use:

```sh
PLAYWRIGHT_BASE_URL=http://127.0.0.1:5183
PLAYWRIGHT_MEILI_URL=http://127.0.0.1:7710
```

## 14. Browser Verification Checklist

After setup, verify the app through a real browser, not screenshots alone.

Required pages:

| Route | Expected authenticated heading or behavior |
| --- | --- |
| `/` | `Operational Overview`; no failed overview. |
| `/records` | `Records`; list loads and rows are openable. |
| `/projects` | `Projects`; real project records/cards are clickable. |
| `/documents` | `Documents`; document list loads with linked records. |
| `/search` | `Search`; filters and URL state work. |
| `/dashboards` | Dashboard heading such as `Engineering Overview`; widgets load. |
| `/tasks` | `Task Inbox`; tasks are visible/openable when present. |
| `/admin` | `Admin Configuration`; published versions/layouts/templates visible. |
| `/audit` | `Audit Timeline`; events load and link to targets when permitted. |
| `/imports` | `Import Wizard`; wizard loads. |

Failure indicators:

- `Sign in` link remains after login.
- `Failed to load`.
- `Unavailable`.
- `API request failed`.
- `Bad Gateway`.
- Empty demo dataset after seed command.
- Search result widgets show irrelevant zero-result panels for exact type filters.

## 15. Search And Navigation Contract

Use structured filters for navigation. Do not fake field filters with plain keywords.

Correct query examples:

```text
status="archived"
type="project"
type="document"
type="raw_material" status="released"
```

When a dashboard, overview card, record type card, or status badge navigates to Search, it must encode the intended field filter in the URL.

## 16. Production Safety

Never run these against real production client data unless a release owner explicitly approves the exact action and rollback path:

- `prepare_client_demo --confirm-destructive-reset`
- Database restore.
- Bulk imports.
- Bulk document relinking.
- Role/user deletion.
- Destructive configuration publish.
- Search rebuild against production during business hours.

Production data should be migrated, imported, or restored through an approved plan, not recreated from demo seed commands.

## 17. Git Hygiene

Before commit:

```sh
git status --short
git diff --cached --name-only
```

Do not stage:

- `.env`
- `.env.*` except `.env.example`
- `node_modules/`
- `frontend/dist/`
- `test-results/`
- `playwright-report/`
- `__pycache__/`
- root `/backups/`
- SQL dumps
- private certificates
- runtime media/uploads

Allowed public docs:

- `README.md`
- `LICENSE`
- `docs/admin-guide.md`
- `docs/operations-guide.md`
- `docs/pilot-rollout.md`
- `docs/release-checklist.md`
- `docs/manual/**`

## 18. Recommended First Actions For A Cold Agent

1. Clone the repo.
2. Read `agent.md`.
3. Create `.env` from `.env.example`.
4. If another stack is running, use the isolated setup override.
5. Start Docker Compose.
6. Run migrations.
7. Run `prepare_client_demo --confirm-destructive-reset` only for local/staging.
8. Run `client_readiness_smoke.py`.
9. Log in as `operations_admin`.
10. Verify the browser routes listed above.
11. Report exact commands, URLs, and pass/fail results.

## 19. Handoff Template

Use this format after setup or changes:

```text
Branch/commit:
- <branch> @ <commit>

Environment:
- Normal or isolated
- Compose project name
- App URL

Setup commands:
- <commands run>

Verification:
- Django check: PASS/FAIL
- Client readiness smoke: PASS/FAIL
- Browser routes verified: <list>
- Demo data confirmed: PASS/FAIL

Credentials:
- Username used: operations_admin
- Password source: local .env RELEASE_ADMIN_PASSWORD
- Do not print production secrets.

Risks:
- <anything not verified or known issue>
```

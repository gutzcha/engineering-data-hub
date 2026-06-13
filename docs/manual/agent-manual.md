# Plastic Engineering Data Hub Agent Manual

## 1. Operating Standard

This repository is client-facing production software for plastic engineering data management. Treat every change as if it will be demonstrated to a client without a second chance.

Agent priorities:

1. Preserve working user flows.
2. Never leak secrets.
3. Prefer precise, field-backed navigation over keyword hacks.
4. Verify before claiming completion.
5. Keep documentation honest and current.
6. Do not silently remove user work or unrelated changes.

Do not describe the product as a demo when working on release behavior. Demo data can be seeded for validation, but the software should behave as a production system.

## 2. Product And Architecture Summary

Plastic Engineering Data Hub is a containerized internal web application.

Runtime services:

| Service | Responsibility |
| --- | --- |
| proxy | Caddy reverse proxy and internal HTTPS. |
| frontend | React/Vite browser application. |
| backend | Django REST API and Django admin runtime. |
| worker | Celery worker for asynchronous jobs. |
| beat | Celery scheduler for periodic jobs. |
| db | PostgreSQL transactional database. |
| redis | Broker/cache for Celery and runtime support. |
| meilisearch | Full-text search engine. |

Core user-facing domains:

- Records.
- Projects.
- Documents.
- Search.
- Dashboards.
- Workflows and task inbox.
- Audit.
- Admin configuration.
- Imports.
- Backups and operations.

## 3. Repository Map

Use these paths first:

| Path | Purpose |
| --- | --- |
| `README.md` | Project entrypoint, quickstart, verification, and docs links. |
| `.env.example` | Safe environment template for Compose defaults and deployment setup. |
| `example.env` | Safe example values for operators copying a local env contract. |
| `compose.yaml` | Production-oriented Docker Compose service graph. |
| `compose.dev.yaml` | Development overrides. |
| `backend/plastic_hub/settings/` | Django settings modules. |
| `backend/plastic_hub/urls.py` | Top-level backend URL routing. |
| `backend/apps/accounts` | Users, roles, permissions, and auth policies. |
| `backend/apps/audit` | Immutable event log and audit APIs. |
| `backend/apps/backups` | Backup manifests, services, tasks, and APIs. |
| `backend/apps/config_registry` | Dynamic configuration, object templates, form layouts, workflows, dashboards. |
| `backend/apps/documents` | Document registry, revisions, storage, extraction, and document APIs. |
| `backend/apps/folders` | Managed folders, folder templates, scanner, and review inbox support. |
| `backend/apps/imports` | Import parser, mapper, validation, and execution APIs. |
| `backend/apps/projects` | Project records, dependency graph, project APIs. |
| `backend/apps/records` | Core record models, serializers, validation, and APIs. |
| `backend/apps/relationships` | Relationship and graph APIs. |
| `backend/apps/reports` | Dashboard/report query APIs. |
| `backend/apps/search` | Search indexing and query APIs. |
| `backend/apps/workflows` | Workflow engine, task models, and task APIs. |
| `frontend/src/app` | Frontend app shell and routes. |
| `frontend/src/components` | Shared UI components. |
| `frontend/src/features` | Feature modules by product area. |
| `frontend/src/lib/api.ts` | Central frontend API client. |
| `frontend/e2e` | Playwright end-to-end flows. |
| `docs/admin-guide.md` | Admin and governance guidance. |
| `docs/operations-guide.md` | Install, backup, restore, and update runbook. |
| `docs/release-checklist.md` | Release acceptance checklist. |
| `docs/manual/user-manual.md` | Human operating manual. |
| `docs/manual/agent-manual.md` | This agent manual. |

## 4. Environment And Secrets

Secrets belong in local or deployment environment files, not in tracked source.

Rules:

- Never commit `.env`.
- Never commit real passwords, tokens, API keys, private certificates, or production host secrets.
- Keep `.env.example` and `example.env` safe for Git by using placeholder values only.
- If a command needs an admin password, read it from an environment variable such as `RELEASE_ADMIN_PASSWORD`.
- If a secret was ever committed, stop and escalate so it can be rotated. Removing it from a later commit is not enough.

Important local files:

| File | Commit status | Purpose |
| --- | --- | --- |
| `.env` | Ignored | Real local or deployment values. |
| `.env.example` | Tracked | Safe template values and required keys. |
| `example.env` | Tracked | Safe sample env contract for operators. |

Production readiness requires replacing every placeholder with a real deployment value before launch.

## 5. Local Startup And Service Commands

Start the development stack:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
```

Check service status:

```sh
docker compose -f compose.yaml -f compose.dev.yaml ps
```

Run migrations:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py migrate
```

Run Django system checks:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py check
```

Run the client-readiness smoke script:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec backend python scripts/client_readiness_smoke.py
```

Build the frontend from the `frontend` directory:

```sh
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
```

If environment variables changed, recreate affected services:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up -d --force-recreate backend worker beat
```

## 5A. Installation And Deployment Runbook

Use this runbook when preparing a fresh environment, validating a deployment, or helping a human operator ship a release.

### 5A.1 Host Prerequisites

Confirm the target host has:

| Category | Requirement |
| --- | --- |
| Operating system | Linux server or Windows Server host approved for Docker workloads. |
| CPU | 4 cores minimum; 8 cores preferred for heavier search/document usage. |
| RAM | 16 GB minimum; 32 GB preferred. |
| Disk | 250 GB SSD minimum; at least 2x managed/media data size available for backups and restore staging. |
| Runtime | Docker Engine or Docker Desktop with Docker Compose v2. |
| Source access | Git access to the approved release branch or tag. |
| Network | Internal DNS name and VPN/internal routing. |
| TLS | Internal certificate/key or approved internal TLS policy. |
| Security | Firewall or network group restricting production access to intended users. |

Host preflight commands:

```sh
git --version
docker --version
docker compose version
```

Do not continue with deployment if Docker Compose is unavailable.

### 5A.2 Source Checkout

Fresh checkout:

```sh
git clone <repository-url> plastic-engineering-data-hub
cd plastic-engineering-data-hub
git checkout <release-branch-or-tag>
```

Existing checkout:

```sh
git fetch --all --prune
git checkout <release-branch-or-tag>
git status --short
```

If `git status --short` shows local changes on a production host, stop and ask the release owner whether those changes are expected.

### 5A.3 Environment File

Create the real environment file from the safe template:

```sh
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Required production review:

| Key | Required condition |
| --- | --- |
| `SECRET_KEY` | Unique non-placeholder value. |
| `POSTGRES_PASSWORD` | Strong non-placeholder value. |
| `DATABASE_URL` | Matches the database password and service name. |
| `MEILI_MASTER_KEY` | Strong non-placeholder value. |
| `APP_HOST` | Production internal host name. |
| `ALLOWED_HOSTS` | Includes the production host. |
| `CSRF_TRUSTED_ORIGINS` | Includes the production HTTPS origin. |
| `TIME_ZONE` | Matches operational backup/reporting expectations. |
| `BACKUP_ROOT` | Points to writable backup storage. |
| `MEDIA_ROOT` | Points to managed document/media storage. |
| `RELEASE_ADMIN_PASSWORD` | Set only in real `.env`, never in tracked files. |
| `CADDY_TLS_DIRECTIVE` | Matches internal TLS plan. |

Search for accidental committed secrets before handoff:

```sh
git status --short
git diff --cached --name-only
```

Expected: `.env` is not staged or committed.

### 5A.4 TLS And Network Setup

Production should publish only the proxy service. Internal services must remain private on the Docker network.

If using mounted certs:

```env
CADDY_TLS_DIRECTIVE=tls /etc/caddy/certs/plastic-hub.crt /etc/caddy/certs/plastic-hub.key
```

Verify:

1. Certificate and key files exist under `ops/caddy/certs/`.
2. File permissions allow the proxy container to read them.
3. `APP_HOST` resolves to the server.
4. Port `443` is reachable only from the intended network.
5. PostgreSQL, Redis, Meilisearch, backend, and frontend are not exposed directly in production.

### 5A.5 Development Startup

Use this for local validation:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
docker compose -f compose.yaml -f compose.dev.yaml ps
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py migrate
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py check
```

Open:

```text
http://127.0.0.1:5173/
```

### 5A.6 Production Startup

Use this for production:

```sh
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml ps
docker compose -f compose.yaml exec backend python manage.py migrate
docker compose -f compose.yaml exec backend python manage.py check
curl -k https://<APP_HOST>/api/health/
```

Expected:

- `proxy`, `backend`, `frontend`, `worker`, `beat`, `db`, `redis`, and `meilisearch` are running or healthy.
- Migrations complete without errors.
- Django check reports no issues.
- Health endpoint responds successfully.

### 5A.7 First-Run Configuration

After production startup:

1. Create or verify a System Admin user.
2. Confirm the user belongs to the System Admin group.
3. Publish or verify the active Plastic Engineering configuration.
4. Confirm record templates exist for product, raw material, product spec, supplier, customer, project, test method, and document.
5. Confirm starter workflows are available.
6. Confirm starter dashboards and layouts are published.
7. Confirm role groups and object permissions match the client rollout plan.
8. Confirm backup path is writable.
9. Confirm Meilisearch indexing is operational.

If using the release preparation command, ensure `RELEASE_ADMIN_PASSWORD` is already present in `.env`, then run the command without embedding the password in the shell command:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py prepare_client_demo --confirm-destructive-reset
```

Only run destructive reset commands in approved local or staging environments. Do not run them against production client data.

### 5A.8 Backup And Restore

Manual backup:

```sh
sh ops/scripts/backup.sh
```

Development backup:

```sh
COMPOSE_FILE_ARGS="-f compose.yaml -f compose.dev.yaml" sh ops/scripts/backup.sh
```

Restore drill on non-production:

```sh
CONFIRM_RESTORE=<backup-id> sh ops/scripts/restore.sh <backup-id>
```

Agent acceptance criteria:

- Backup command completes.
- Manifest exists.
- Database dump exists.
- Managed/media files are included.
- Restore has been practiced on a non-production copy before production cutover.

### 5A.9 Update And Rollback Procedure

Update:

1. Announce maintenance window.
2. Run manual backup.
3. Record backup id.
4. Fetch approved release.
5. Rebuild services.
6. Run migrations.
7. Run backend check.
8. Run frontend/browser acceptance checks.
9. Confirm search and dashboards.
10. Release users.

Commands:

```sh
sh ops/scripts/backup.sh
git fetch --all --prune
git checkout <release-branch-or-tag>
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml exec backend python manage.py migrate
docker compose -f compose.yaml exec backend python manage.py check
curl -k https://<APP_HOST>/api/health/
```

Rollback:

1. Stop and notify the release owner.
2. Capture failing symptoms, URLs, logs, and timestamps.
3. Decide whether to roll back code, restore data, or both.
4. If data restore is required, use a verified backup id.
5. Run restore only with explicit confirmation.
6. Re-run health, search, and browser checks.

Never improvise production rollback while users are actively writing data.

### 5A.10 Deployment Troubleshooting

| Symptom | First checks |
| --- | --- |
| Browser cannot reach app | DNS, firewall, proxy service, port `443`, certificate configuration. |
| Login fails for all users | Backend logs, database connectivity, auth settings, user records. |
| Static frontend loads but API fails | `APP_HOST`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, proxy routing, backend health. |
| Search empty or stale | Meilisearch service health, master key, indexing task logs, search rebuild status. |
| Document upload fails | Media volume permissions, file size limits, backend logs, user permissions. |
| Worker tasks do not run | Redis health, worker logs, beat logs, Celery configuration. |
| Backups fail | `BACKUP_ROOT`, volume permissions, disk space, database dump access. |
| Admin shows no published layouts | Active configuration publish state, config registry data, dashboard/layout seed status. |

## 6. Data Readiness And Release Dataset

A release-ready local dataset should include meaningful plastic engineering content, not empty or toy data.

Minimum expectations:

- Active users required for the release are present.
- At least three real project records exist.
- Raw materials, products, product specs, suppliers, customers, test methods, and documents are represented.
- Documents are linked to relevant records.
- Project pages show project documents.
- Workflow tasks are openable and linked to relevant records.
- Search indexes records, documents, folder events, and projects.
- No QA noise appears in the user interface.

The client-readiness smoke script is the minimum non-browser data gate:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec backend python scripts/client_readiness_smoke.py
```

Expected result includes:

```text
Client-readiness smoke: PASS
```

If the smoke script fails, do not claim the system is ready.

## 7. Search And Navigation Contract

Search is the canonical discovery surface. Pages that need to show a subset of records should navigate to Search with precise filters encoded in the URL.

Correct examples:

```text
status="archived"
type="project"
type="document"
type="raw_material" status="released"
```

Incorrect patterns:

```text
archived
project
document
released raw material
```

Why this matters:

- A document title can contain the word `project` without being a project.
- A record note can contain `archived` without having status `archived`.
- Keyword-only navigation creates false positives and client-visible confusion.

When a filter narrows result type, irrelevant result widgets should not remain visible with zero results. For example, `type="project"` should focus the Search UI on relevant project results rather than showing unrelated empty sections.

## 8. Browser QA Contract

Use the in-app browser or Playwright when validating user-facing behavior. A page loading without a console crash is not enough. Click through the actual workflow.

Required browser checks before claiming client readiness:

| Area | Required behavior |
| --- | --- |
| Home | Operational overview loads and count cards are clickable. |
| Records | Record list loads, filters work beyond status, rows open record details. |
| Projects | Project cards or rows are real data and open project pages. |
| Project detail | Linked records, documents, timeline, and tasks are accessible. |
| Documents | Document list loads, documents open, uploads/revisions can be exercised in a safe environment. |
| Search | Filters are structured, URLs preserve query state, irrelevant widgets disappear under type filters. |
| Dashboards | Widgets can be selected, moved/resized where supported, saved, and clicked into precise Search queries. |
| Tasks | Inbox tasks are clickable and open linked work. |
| Audit | Audit rows link to relevant records, documents, tasks, or config objects. |
| Admin | Published versions, layouts, templates, users, and widgets are understandable and actionable. |
| Imports | Wizard loads, mapping and validation states work, sample import path is not broken. |

If a user specifically reports a broken click target, reproduce the click. Do not inspect only the source code.

## 9. Verification Matrix

Use the smallest verification that proves the claim.

Backend health:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py check
```

Client data readiness:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec backend python scripts/client_readiness_smoke.py
```

Frontend type/build check:

```sh
cd frontend
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
```

Focused backend traceability flow:

```sh
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps -e DJANGO_SETTINGS_MODULE=plastic_hub.settings.test backend pytest tests/e2e/test_traceability_flow.py
```

Playwright traceability flow:

```sh
cd frontend
E2E_USERNAME=<test-user> E2E_PASSWORD=<test-password> npx playwright test e2e/traceability.spec.ts
```

Do not use real production credentials for automated tests unless the release owner explicitly approves the target and account.

## 10. Change Workflow For Agents

Before editing:

1. Identify exactly which files need to change.
2. Read each required file once.
3. Decide the intended write set.
4. Avoid unrelated refactors.
5. Preserve user changes and unrelated work.

During editing:

1. Keep runtime changes separate from documentation changes when possible.
2. Use environment variables for secrets and deploy-specific values.
3. Prefer field filters and typed contracts over display-string matching.
4. Update tests or docs when behavior changes.
5. Do not remove safety checks for speed.

After editing:

1. Run verification appropriate to the change when permitted or required.
2. Report exactly what passed.
3. Report anything not verified.
4. Do not claim perfection beyond evidence.
5. If committing, ensure `.env`, generated artifacts, and local reports are not staged.

## 11. Documentation Workflow

Documentation should be maintained with the same care as code.

When adding or changing behavior, update the relevant docs:

| Behavior changed | Docs to consider |
| --- | --- |
| Setup, env, services | `README.md`, `docs/operations-guide.md`, `.env.example`, `example.env`. |
| Admin/config behavior | `docs/admin-guide.md`, `docs/manual/user-manual.md`. |
| Release process | `docs/release-checklist.md`, `docs/operations-guide.md`. |
| User workflow | `docs/manual/user-manual.md`. |
| Agent workflow or maintenance process | `docs/manual/agent-manual.md`. |

Documentation standards:

- Say what the user can do, not just what the code contains.
- Include concrete examples for search and operational commands.
- Do not publish real credentials.
- Keep instructions aligned with current routes and service names.
- Avoid vague promises such as "works as expected" without a behavior statement.

## 12. Safety Rules

Never do these without explicit instruction and a safe rollback plan:

- Delete user data.
- Reset the database.
- Run destructive imports.
- Change production secrets.
- Disable authentication or permissions.
- Remove audit logging.
- Commit `.env` or private keys.
- Replace production documents with sample files.
- Revert unrelated user changes.

High-risk actions require an explicit pause:

- Schema migrations that remove or rename fields.
- Configuration publishes with destructive template changes.
- Search index rebuilds against production data.
- Restore operations.
- Bulk document relinking.
- User or role deletion.

## 13. Handoff Template

Use this structure when handing work back to a human or another agent:

```text
Summary:
- What changed.
- Why it changed.
- Main files touched.

Verification:
- Command run: <command>
- Result: PASS or FAIL with key output.
- Browser checks: pages and interactions verified.

Secrets:
- Confirm `.env` was not committed.
- Confirm any new env keys were added to `.env.example` or `example.env` with safe values.

Risks:
- Known gaps.
- Anything not verified.
- Required deployment steps.

Next steps:
- Exact recommended follow-up actions.
```

If work was committed and pushed, include the branch and commit hash.

## 14. Known Client-Critical Behaviors

These behaviors are client-critical and should be preserved through every change:

- Home operational overview must not be frozen.
- Records must load, filter broadly, and open details without breaking the app.
- Projects must be real records and clickable into project pages.
- Documents must be present, openable, and linked to relevant records.
- Search must support structured filters and URL-copyable query state.
- Dashboard widgets must be configurable where supported and must navigate through precise field filters.
- Task inbox rows must open tasks or linked work.
- Audit rows must link to relevant targets.
- Admin must expose published versions, layouts, users, templates, widgets, and safety controls clearly.
- Imports must load and validate mappings without breaking existing app state.

When a user says something is broken in one of these areas, treat it as release-critical until proven otherwise.


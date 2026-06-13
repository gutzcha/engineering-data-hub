<!--
===
File Summary
Path: docs\superpowers\codebase-index.md
Type: markdown
Purpose: Agent workflow and documentation for indexing, planning, and subagent coordination.
Primary responsibilities:
- Domain behavior is summarized for fast onboarding and avoids full-file reread.
- Core symbols: Plastic Engineering Data Hub — Canonical Codebase Index
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

# Plastic Engineering Data Hub — Canonical Codebase Index

- Last indexed by: codex-agent
- Indexed at: 2026-06-09T12:00:00Z
- Next refresh trigger: any DB migration, API contract change, route change, or operational script update.

## 1. Project Purpose and Architecture
Plastic Engineering Data Hub is a containerized engineering execution platform with:
- Django REST backend for traceable records, documents, workflows, search, and governance.
- React/Vite frontend for operational UIs (projects, records, documents, searches, workflows, admin config).
- Worker layer for asynchronous tasks via Celery + Redis.
- Meilisearch for search indexing.
- PostgreSQL for transactional storage.
- Caddy reverse proxy for frontend/backend traffic in compose.

## 2. Backend Domain Map
Core backend domains and app partitions:
- `backend/apps/accounts` — users, roles, permissions, auth policies.
- `backend/apps/audit` — immutable logs and retrieval APIs.
- `backend/apps/backups` — backup manifests and operational backup services.
- `backend/apps/config_registry` — dynamic UI/business configuration with versioning.
- `backend/apps/documents` — documents/revisions and extraction tasks.
- `backend/apps/folders` — folder events, templates, scanning, tasks.
- `backend/apps/imports` — parser/mapper-based import tooling.
- `backend/apps/projects` — project entity model and dependency graphs.
- `backend/apps/records` — core traceability records and code validation.
- `backend/apps/relationships` — relationship APIs and graph utilities.
- `backend/apps/reports` — report models and computed query APIs.
- `backend/apps/search` — search payload indexing and query API.
- `backend/apps/workflows` — task definitions and execution engine.
- See `docs/superpowers/index-drafts/backend.md` for full per-app detail and exact file paths.

## 3. API Surface Map
Backend URL composition flows through:
- `backend/plastic_hub/urls.py` for global include mapping.
- app-level routers in each `backend/apps/*/urls.py`.
- workflow endpoints and service hooks exposed by `backend/apps/workflows/views.py`.
- API client callers are centralized in `frontend/src/lib/api.ts`.
- Notable API families: accounts, projects, records, folders, documents, imports, search, audits, reports, workflows, and configs.

## 4. Frontend Domain Map
Frontend structure under `frontend/src`:
- Routing shell: `src/main.tsx`, `src/app/App.tsx`, `src/app/routes.tsx`.
- Shared UI: `src/components/AppLayout.tsx`, `DataTable.tsx`, `StatusBadge.tsx`.
- Feature modules for records, projects, documents, folders, imports, dashboards, workflows, search, audit, and config admin.
- Test surface across feature-level `*.test.tsx`.
- E2E traceability flow in `frontend/e2e/traceability.spec.ts`.
- API client library: `frontend/src/lib/api.ts`.
- See `docs/superpowers/index-drafts/frontend.md` for detailed route and ownership mapping.

## 5. Asynchronous Jobs and Infrastructure
- Celery app bootstrap: `backend/plastic_hub/celery.py`.
- Scheduled/background tasks in `backend/apps/*/tasks.py` (notably backups, search reindex, workflows).
- Operational scripts in `ops/scripts/*.sh` and compose worker/beat services.

## 6. Data Model and Relationships
- Core entities in `backend/apps/*/models.py`.
- Relationship handling through records, folders, and project graph modules:
  - project dependency links
  - folder-event/change links
  - relationship graph APIs in `backend/apps/relationships`
  - workflow task ownership and state transitions.
- Migration state in `backend/apps/*/migrations/*.py` controls schema evolution.

## 7. Configuration and Runtime Surface
- Settings stack: `backend/plastic_hub/settings/base.py`, `dev.py`, `prod.py`, `test.py`.
- Env contract from `.env.example` and compose services (`compose.yaml`, `compose.dev.yaml`).
- Dockerized services in `backend/Dockerfile`, `frontend/Dockerfile`, plus `ops/caddy/Caddyfile`.
- Runtime docs and entrypoints in `README.md`, `docs/operations-guide.md`, and Makefile commands.
- See `docs/superpowers/index-drafts/ops-docs.md`.

## 8. Docs and Runbooks Index
- `README.md` for project entry, setup, and contributor context.
- `docs/admin-guide.md` for governance/operations.
- `docs/operations-guide.md` for backups and restore operations.
- `docs/release-checklist.md` and `docs/pilot-rollout.md` for release and rollout controls.
- `agent.md` and all files in `docs/superpowers/index-drafts/` for indexing workflow.

## 9. Testing and Validation Matrix
- Backend test command family: `make test`, health and settings checks, and targeted `backend/tests/**` modules.
- Frontend unit/integration: `make frontend-test`, Vitest suites in `frontend/src/**/**/*.test.tsx` and `frontend/src/lib/api.test.ts`.
- E2E: `frontend/e2e/traceability.spec.ts`.
- For full list see `docs/superpowers/index-drafts/testing.md`.

## 10. Known Risks and Follow-up Actions
- Keep this index synchronized with API migrations and compose changes.
- Ensure migrations and model changes are paired with `backend/tests/*` updates.
- Verify front-end route changes against backend contracts to prevent drift.
- Refresh summaries after any feature or schema addition.

## Discovery Contract (Single-Index Expectations)
- Every scanned file that can carry comments includes a top-of-file summary block using `===` separators.
- Agents should read these summaries first, then open files only for deep context.
- Summary files:
  - `docs/superpowers/index-drafts/backend.md`
  - `docs/superpowers/index-drafts/frontend.md`
  - `docs/superpowers/index-drafts/ops-docs.md`
  - `docs/superpowers/index-drafts/testing.md`

Note: JSON files (for example `package.json`, `tsconfig.json`, `frontend/package-lock.json`) are intentionally excluded from inline comments to avoid breaking parser expectations; use this index plus module-level imports for onboarding those artifacts.

Last indexed by: codex-agent
Indexed at: 2026-06-09T12:00:00Z
Next refresh trigger: any configuration publish, schema migration, or release handoff.
Next reviewer: platform owner or next onboarding agent.


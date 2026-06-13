# Plastic Engineering Data Hub — Agent Reference

## Project Perspective

Plastic Engineering Data Hub is an internal, self-hosted engineering execution platform for plastic material/product workflows. It combines a Django REST backend, React frontend, and Dockerized service mesh (PostgreSQL, Redis, Celery, Meilisearch, and Caddy reverse proxy) to support controlled recordkeeping, document workflows, search, and operational control (backups, restores, audits, and role-based governance).

Primary mission:
- Capture and validate traceable engineering records (product, raw material, spec, supplier, customer, project, document).
- Coordinate release/approval workflows with auditability.
- Link controlled documents, managed folders, and relationships between records.
- Provide dashboards, reporting, and search for production-use visibility.
- Support repeatable operations via scripts, scheduled jobs, and documented runbooks.

## Architecture Snapshot

- `compose.yaml`: service topology and containerized dependencies.
- `compose.dev.yaml`: local development overrides.
- `backend/`: Django app server, API, Celery worker/beat, business rules.
- `frontend/`: React/Vite client and Playwright/Vitest test harness.
- `docs/`: operations, admin, release, and rollout documentation.
- `ops/`: deployment scripts, proxy assets, and environment-specific operational files.

`backend` runs from Django with apps in:
- `backend/apps/accounts`
- `backend/apps/api`
- `backend/apps/audit`
- `backend/apps/backups`
- `backend/apps/config_registry`
- `backend/apps/documents`
- `backend/apps/folders`
- `backend/apps/imports`
- `backend/apps/projects`
- `backend/apps/records`
- `backend/apps/relationships`
- `backend/apps/reports`
- `backend/apps/search`
- `backend/apps/workflows`

`frontend` surface starts at:
- `frontend/src/main.tsx`
- `frontend/src/app/`
- `frontend/src/components/`
- `frontend/src/features/`
- `frontend/src/lib/`
- `frontend/src/test/`
- `frontend/e2e/` for end-to-end traceability flows.

## Single-Index Deliverable (Required)

All future onboarding agents should create and maintain one canonical index at:
- `docs/superpowers/codebase-index.md`

This index should include at a minimum:
- Project purpose and architecture summary.
- Backend app matrix (purpose, models, key endpoints, tests).
- Frontend feature matrix (views/routes, forms, state, API clients, tests).
- Database and workflow model inventory.
- Scheduled/asynchronous tasks and integration points.
- Environment/configuration inventory (`.env`, compose, scripts).
- Docs/runbook index and operational command surface.
- Known risks, missing coverage areas, and next maintenance tasks.

## Subagent Dispatch Instructions

When expanding the index, dispatch focused subagents (or focused passes) using this partition:

1. `backend-scan`
- Scope: `backend/`
- Deliverable: `docs/superpowers/index-drafts/backend.md`
- Goal: summarize app responsibilities, models, serializers/views, tasks, and tests.

2. `frontend-scan`
- Scope: `frontend/`
- Deliverable: `docs/superpowers/index-drafts/frontend.md`
- Goal: summarize routing/feature modules, API integration points, state management, and UI test coverage.

3. `infra-docs-scan`
- Scope: `ops/`, `docs/`, root-level compose/Makefile scripts
- Deliverable: `docs/superpowers/index-drafts/ops-docs.md`
- Goal: summarize deployment, environment variables, backup/restore, and runbook links.

4. `quality-test-scan`
- Scope: `backend/tests/`, `frontend/test/`, `frontend/e2e/`
- Deliverable: `docs/superpowers/index-drafts/testing.md`
- Goal: summarize coverage surface, acceptance criteria, and recurring execution commands.

Consolidation rule:
- Merge every draft into `docs/superpowers/codebase-index.md` only after all four sections are complete.
- Keep one source-of-truth summary with consistent terminology, file references, and command conventions.
- Do not duplicate old stale summaries in root docs.

## Code Summary Header Contract (for future scans)

All subagents must add or refresh a compact summary directly at the top of every code/document file they inspect before finalizing conclusions. This lets future agents scan context from file headers first and avoid re-reading full implementations.

Required format:

```text
===
File Summary
Path: <relative/path/to/file>
Type: <python | typescript | markdown | shell | yaml | json>
Purpose: <single-sentence purpose>
Primary responsibilities:
- ...
Inputs:
- ...
Outputs:
- ...
Dependencies:
- ...
Known risks:
- ...
===
```

Contract rules:
- If a file already has a summary block, update it instead of adding a duplicate.
- Keep one block at the very top per file.
- Keep entries brief and evidence-based.

Index expectation:
- `docs/superpowers/codebase-index.md` must include a section describing this contract and a directory-to-summary map so agents can initialize from summaries before opening full files.

## Initialization Checklist

1. Confirm working tree is clean enough for a new run (`git status --short`).
2. Ensure environment baseline exists (`.env.example`, `compose.yaml`, `compose.dev.yaml`, `Makefile`).
3. For local startup: `make dev`.
4. For backend checks: `make test`.
5. For frontend checks: `make frontend-test`.
6. For migration: `make migrate`.
7. For linting: `make lint`.

## Operational Context

- Backup orchestration and restore are in `ops/scripts/` and documented in `docs/operations-guide.md` + `docs/release-checklist.md`.
- Release and pilot governance are documented in `docs/release-checklist.md` and `docs/pilot-rollout.md`.
- Admin and governance flows are documented in `docs/admin-guide.md`.

## Agent Working Rule

Before any new work, read this file, `README.md`, and `docs/superpowers/plans/<latest-plan>.md`. Then scan required scopes, update `docs/superpowers/codebase-index.md` as the single canonical map, and only then begin implementation.

## Extended Onboarding Model

This repository is a Django + React platform with explicit onboarding contracts:

- Keep one canonical map in `docs/superpowers/codebase-index.md`.
- Keep one domain draft per area in `docs/superpowers/index-drafts/{backend,frontend,ops-docs,testing}.md`.
- Keep every touched code file with a top-of-file summary header so agents can triage intent quickly.
- Prefer reading summaries and index files first, then open full files only when implementing.

Canonical files to anchor every implementation handoff:
- `docs/superpowers/codebase-index.md`: single source for project purpose, architecture, and risks.
- `docs/superpowers/index-drafts/backend.md`: per-domain backend contracts.
- `docs/superpowers/index-drafts/frontend.md`: route ownership and feature ownership map.
- `docs/superpowers/index-drafts/ops-docs.md`: ops, deployment, backup, and governance map.
- `docs/superpowers/index-drafts/testing.md`: validation and test-coverage matrix.

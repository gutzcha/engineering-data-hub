<!--
===
File Summary
Path: docs\superpowers\index-drafts\ops-docs.md
Type: markdown
Purpose: Agent workflow and documentation for indexing, planning, and subagent coordination.
Primary responsibilities:
- Domain behavior is summarized for fast onboarding and avoids full-file reread.
- Core symbols: Ops and Docs Summary Draft
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

# Ops and Docs Summary Draft

- Scope: docs/, ops/, root config and compose files
- Owner: infra-docs-scan
- Indexed at: 2026-06-09T12:00:00Z

## Architecture and Deployment
- Local and deployed stacks described by `compose.yaml` and `compose.dev.yaml`.
- Runtime services: db (PostgreSQL), redis, backend, frontend, worker, beat, meilisearch, caddy.
- `backend/Dockerfile`, `frontend/Dockerfile` build images; `ops/caddy/Caddyfile` handles reverse proxy and static assets.
- Environment defaults and required variables in `.env.example` and app-specific settings.

## Operational Procedures
- Backup: `ops/scripts/backup.sh`; manifest and artifact handling in docs and backup app APIs.
- Restore: `ops/scripts/restore.sh` + `docs/operations-guide.md`.
- Installation/runbooks: `ops/scripts/install-linux.md`, `ops/scripts/install-windows-server.md`.
- Governance: `docs/admin-guide.md`, `docs/pilot-rollout.md`, `docs/release-checklist.md`.

## Data & Compliance Surfaces
- Compose file pins service dependencies and port exposure.
- `Makefile` defines local workflows for setup, build, test, lint, migrations, and backup/restore operations.
- `docs` files describe operational ownership, approval gates, and incident workflows.

## Risks and maintenance notes
- Keep environment and secrets synchronized between `.env.example`, compose templates, and service docs.
- Meilisearch and Redis tuning requires periodic review during scaling.
- Database migrations and fixture seeds should be replayed carefully during restore.


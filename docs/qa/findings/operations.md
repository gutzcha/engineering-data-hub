# Operations QA Findings

Date: 2026-06-08

Status: passed after fixes.

## Coverage

`frontend/e2e/client-readiness-operations.spec.ts` covers authenticated route health, relationships, search, saved views, dashboards, project operations, CSV imports, XLSX exports, backups, folder events, workflow tasks, and controlled JSON responses.

## Findings Closed

- `QA-PROJ-001`: project task move failed on PostgreSQL due to a nullable joined `FOR UPDATE` query. Fixed in project services and covered by backend plus Playwright tests.
- `QA-BACKUP-001`: backup creation returned an HTML HTTP 500 when `pg_dump` was unavailable. Fixed with the PostgreSQL client in the backend image and controlled service errors for missing binaries and nonzero `pg_dump` exits.
- `QA-OPS-ROUTE-CONSOLE`: authenticated route health originally exposed `/admin` route/proxy and permission noise. Fixed by route ownership changes and by running the route health check with the correct seeded system-admin role.

## Non-Blocking Depth Note

Folder event accept, ignore, assign, link-document, permission filtering, and indexing are covered by backend tests. Playwright coverage intentionally gates the browser route and controlled JSON responses to avoid race-prone stateful folder mutations in the parallel desktop/mobile browser matrix.

## Evidence

- `frontend/e2e/client-readiness-operations.spec.ts`
- `backend/apps/projects/services.py`
- `backend/apps/backups/services.py`
- `backend/tests/projects/test_projects.py`
- `backend/tests/backups/test_backup_manifest.py`

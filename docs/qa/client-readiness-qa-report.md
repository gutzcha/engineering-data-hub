# Client Readiness QA Report

Date: 2026-06-08

## Summary

The client-readiness QA suite now covers the core Plastic Engineering Data Hub workflows end to end. It creates records, edits and releases them, proves records cannot be deleted, archives records instead, creates record versions, uploads a real plastic-related PDF from the internet, releases controlled document revisions, checks document library browsing, validates admin permission boundaries, exercises projects, relationships, imports, exports, backups, audit, search, folders, dashboards, and workflow tasks.

Final automated status: all checks passed.

## External Test Document

The document lifecycle test downloads and uploads the Plastic-Craft polycarbonate PDF:

https://plastic-craft.com/content/SDS/polycarbonate.pdf

The QA helper stores the downloaded PDF and SHA-256 checksum under ignored Playwright test artifacts, then uploads the actual PDF bytes through the app's multipart document API.

## Automated Evidence

- Playwright client-readiness suite: 34 passed across Chromium desktop and Chromium mobile.
- Backend regression suite: 229 passed.
- Frontend unit suite: 26 passed across 14 files.
- Frontend typecheck/lint: passed.
- Docker stack was rebuilt and recreated from this QA worktree before the final browser run.

## Fixed Findings

### QA-REC-001: Records Had No Archive Flow

Severity: Critical

Status: Fixed.

Impact: Users needed a safe alternative to deletion. The app now exposes record archive behavior, preserves audit history, and keeps DELETE unavailable.

Review-loop hardening: archive now has explicit negative permission coverage proving non-admin engineers cannot archive records.

Evidence: `backend/apps/records/models.py`, `backend/apps/records/views.py`, `backend/tests/records/test_records.py`, `frontend/e2e/client-readiness-records.spec.ts`.

### QA-REC-002: Records Had No Version History

Severity: Critical

Status: Fixed.

Impact: Users needed controlled snapshots before changing important record data. The app now supports record version creation and listing with immutable snapshot payloads.

Review-loop hardening: version tests prove saved snapshots remain unchanged after the live record is edited.

Evidence: `backend/apps/records/models.py`, `backend/apps/records/serializers.py`, `backend/apps/records/views.py`, `backend/apps/records/migrations/0003_recordversion_archived_status.py`.

### QA-DOC-001: Document Revision Release Failed On PostgreSQL

Severity: High

Status: Fixed.

Impact: Releasing a controlled document revision returned HTTP 500 because PostgreSQL rejected `FOR UPDATE` on nullable joined relations. The lock query now avoids nullable joins, and the release lifecycle passes with a real polycarbonate PDF.

Evidence: `backend/apps/documents/views.py`, `backend/tests/documents/test_revisions.py`, `frontend/e2e/client-readiness-documents.spec.ts`.

### QA-DOC-002: Document Library Could Not List Or Retrieve Documents

Severity: Medium

Status: Fixed.

Impact: Users could see documents from source records but could not browse the document workspace or open document detail pages. The backend now supports list/retrieve with record-level view checks, and the frontend document workspace/detail page renders controlled document metadata.

Evidence: `backend/apps/documents/views.py`, `backend/tests/documents/test_revisions.py`, `frontend/src/features/documents/DocumentPanel.tsx`, `frontend/e2e/client-readiness-documents.spec.ts`.

### QA-ROUTE-001: Direct `/admin` Reload Fell Through To Django Admin

Severity: High

Status: Fixed.

Impact: Direct browser reloads of the React Admin workspace could show the Django admin route through the frontend dev proxy. The frontend dev proxy no longer captures `/admin`, so React routing owns the workspace route.

Evidence: `frontend/vite.config.ts`, `frontend/e2e/client-readiness-records.spec.ts`.

### QA-PROJ-001: Project Task Move Failed On PostgreSQL

Severity: High

Status: Fixed.

Impact: Moving project board tasks returned HTTP 500 because PostgreSQL rejected `FOR UPDATE` on a nullable joined column. The lock query now avoids nullable joins.

Evidence: `backend/apps/projects/services.py`, `backend/tests/projects/test_projects.py`, `frontend/e2e/client-readiness-operations.spec.ts`.

### QA-BACKUP-001: Backup Creation Returned HTML 500 When `pg_dump` Was Missing

Severity: High

Status: Fixed.

Impact: A system-admin backup request returned an HTML Django error page instead of a controlled JSON/API response. The backend image includes the PostgreSQL client, and the backup service now raises a controlled `BackupError` if the binary is missing.

Review-loop hardening: nonzero `pg_dump` exits are also converted to controlled `BackupError` responses instead of leaking raw subprocess failures.

Evidence: `backend/apps/backups/services.py`, `backend/tests/backups/test_backup_manifest.py`, final Playwright backup coverage.

## Client-Readiness Coverage

- Records: create through UI/API, edit, release, archive, version snapshots, delete prevention, audit coverage.
- Admin/config: role separation, normal-user blocks, config-admin authority, destructive field-removal prevention.
- Documents: real PDF download/upload, extraction preview, PDF download, revision release, released revision protection, library list/detail.
- Search/traceability: product, material, specification, relationship, document extraction text, audit surfacing.
- Projects: workload, board, timeline, task move, dependency creation, self/circular dependency rejection.
- Imports/exports: multipart CSV dry-run/apply, records/audit/project-status XLSX downloads.
- Operations: authenticated route health, dashboards, saved views, folders, workflow tasks, backups, JSON response gates.
- Access: seeded QA roles for engineer, config admin, system admin, and read-only user.
- Folder review actions: accept, ignore, assign, link-document, permission filtering, and indexing are covered by backend tests; Playwright keeps browser coverage to authenticated route and controlled JSON health.

## Remaining Risk

No blocking product bugs were detected by the final automated suite. Remaining risk is outside this local QA scope: production network/TLS/SSO, real company file shares, restore drills on client infrastructure, non-Chromium browsers, and load/performance testing.

## How To Run

From `frontend`:

```powershell
$env:PLAYWRIGHT_BASE_URL='http://localhost:5173'
$env:ALLOW_E2E_USER_SEEDING='true'
$env:E2E_PASSWORD='qa-password-12345'
npx playwright test
```

From the repo root:

```powershell
npm --prefix frontend run lint
npm --prefix frontend test -- --run
& 'E:\plastic-engineering-data-hub\backend\.venv\Scripts\python.exe' -m pytest backend\tests
```

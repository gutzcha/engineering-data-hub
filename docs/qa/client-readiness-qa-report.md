# Client Readiness QA Report

Date: 2026-06-08

## Current Status

This report supersedes the earlier one-PDF QA summary. The new client-readiness sweep targets the Home operational overview, document action UI, record archive/version workflows, status filter correctness, local-only population seeding, and 20 public plastic-related PDF uploads.

Final verification has now been completed against the local Docker stack. The strict browser sweep ran with readiness gates enabled and no skipped client-readiness paths.

## Confirmed Bugs Found

### QA-HOME-001: Home Operational Overview Used Fake Static Counts

Severity: Critical

Status: Fixed in code; focused Vitest verified.

Evidence found:

- Static Home metrics showed `128` open records, `17` pending review, `4` blocked tasks, and `312` controlled documents.
- Recent Record Activity showed static record IDs such as `PE-1042`.
- Recent records were not clickable real records.

Fix:

- Home now fetches `/records/`, `/workflow-tasks/?state=open`, and `/documents/`.
- Metrics are computed from live API data.
- Recent activity is sorted by record timestamps and record codes link to `/records/:id`.
- The inert Home export button was removed.

Verification:

- `npm --prefix frontend test -- --run src/app/App.test.tsx`
- `npm --prefix frontend test -- --run src/app/clientReadinessStaticAudit.test.ts`

### QA-DOC-003: Document Preview And Audit Opened Raw JSON

Severity: High

Status: Fixed in code; focused Vitest verified.

Evidence found:

- `Preview` linked directly to `/api/documents/:id/preview/`.
- `Audit` linked directly to `/api/documents/:id/audit/`.
- `Open` only repeated document metadata and did not offer useful preview/audit surfaces.

Fix:

- `Preview` routes to `/documents/:id?view=preview`.
- `Audit` routes to `/documents/:id?view=audit`.
- Document detail renders formatted Preview and Audit panels.
- Download remains a direct file download.
- Existing documents now have an Add Revision UI.

Verification:

- `npm --prefix frontend test -- --run src/features/documents/DocumentPanel.test.tsx src/app/clientReadinessStaticAudit.test.ts`

### QA-REC-003: Archive And Version History Were API-Only

Severity: High

Status: Fixed in code; focused Vitest verified.

Evidence found:

- Backend archive/version endpoints existed, but users could not archive or view/create versions from the record detail page.

Fix:

- Record detail now exposes Archive with confirmation.
- Record detail now exposes Version History and Create Version.
- Record delete remains unavailable.

Verification:

- `npm --prefix frontend test -- --run src/features/records/RecordDetail.test.tsx`

### QA-UI-001: Client-Facing Inert Or Incorrect Controls

Severity: Medium

Status: Fixed for confirmed instances; static guard added.

Evidence found:

- Records page had an inert `Configure View` button.
- Dashboard header showed `Direct Load`.
- Task Inbox showed a disabled `Find` button even though filtering happens live.
- Saved View status options included unsupported `blocked` and omitted `archived`.

Fix:

- Removed inert Records `Configure View`.
- Replaced dashboard `Direct Load` with `No Dashboard Selected`.
- Removed disabled Task Inbox `Find`; search input live filtering is tested.
- Saved View and Record status filters now use `draft`, `released`, `archived`.

Verification:

- `npm --prefix frontend test -- --run src/features/dashboards/DashboardPage.test.tsx src/features/workflows/TaskInbox.test.tsx`
- `npm --prefix frontend test -- --run src/app/clientReadinessStaticAudit.test.ts`

### QA-SEED-001: Full Population Plan Assumed APIs That Do Not Exist

Severity: Critical

Status: Fixed in plan and code; focused backend test verified.

Evidence found:

- Project creation, workflow task creation, and folder event creation are not fully available through public app APIs.

Fix:

- Added a local-only Django command: `seed_client_readiness_demo`.
- Command refuses unsafe targets unless `ALLOW_CLIENT_READINESS_SEED=true` or local DEBUG conditions are met.
- Command creates run-stamped projects, project tasks, workflow tasks, managed folders, folder events, dashboard widgets, and a JSON manifest.

Verification:

- `& 'E:\plastic-engineering-data-hub\backend\.venv\Scripts\python.exe' -m pytest backend\tests\api\test_seed_client_readiness_demo.py`

### QA-DOC-004: Uploaded PDF Extraction Could Save NUL Bytes And Return HTML 500

Severity: High

Status: Fixed in code; backend regression and full Playwright verified.

Evidence found:

- Full population upload of real plastic PDFs triggered `PostgreSQL text fields cannot contain NUL (0x00) bytes`.
- The API returned Django debug HTML instead of controlled JSON.

Fix:

- Document extraction now removes NUL bytes before saving extracted text.
- Regression coverage verifies the sanitizer before database persistence.

Verification:

- `& 'E:\plastic-engineering-data-hub\backend\.venv\Scripts\python.exe' -m pytest backend\tests\documents\test_extraction.py`
- Full strict Playwright population upload completed with 20 controlled documents.

### QA-E2E-001: Browser QA Suite Used Unsafe Parallelism Against One Shared DB

Severity: Medium

Status: Fixed in QA configuration.

Evidence found:

- Eight concurrent Playwright workers caused cross-test data races and list/loading flakes while the 20-PDF population test mutated the same local database.

Fix:

- Playwright now defaults to one worker for deterministic shared-stack QA.
- `PLAYWRIGHT_WORKERS` can still be set explicitly for intentional stress runs.

Verification:

- Full strict Playwright suite passed with 38/38 tests using one worker.

### QA-UI-002: Loading States Displayed Misleading Zero Counts

Severity: Medium

Status: Fixed in code; full Playwright verified.

Evidence found:

- Home could show `0` records/documents while records or documents were still loading.
- The Documents page could show an empty library message before the library request finished.

Fix:

- Home metrics now display `Loading` independently per data source.
- Recent Record Activity now depends only on the records query loading state.
- Document Library now displays a loading state instead of a false empty list.

## Population Coverage Added

- Added `frontend/e2e/support/plasticPdfManifest.ts` with 20 public plastic-related PDF sources.
- Added `downloadPlasticPdfSet()` with SHA-256 recording and explicit generated-fallback marking.
- Added `frontend/e2e/client-readiness-population.spec.ts` to create:
  - 10 suppliers
  - 20 raw materials
  - 15 products
  - 12 product specs
  - 20 controlled documents uploaded from the PDF manifest
  - local-only project/workflow/folder/dashboard seed data through `seed_client_readiness_demo`
- Population run writes `docs/qa/findings/population-run.md`.

## Final Verification Evidence

```powershell
$env:PLAYWRIGHT_BASE_URL='http://localhost:5173'
$env:ALLOW_E2E_USER_SEEDING='true'
$env:E2E_PASSWORD='qa-password-12345'
$env:QA_POPULATE_FULL_DATASET='true'
$env:ALLOW_CLIENT_READINESS_SEED='true'
$env:STRICT_CLIENT_READINESS='true'
npm exec -- playwright test --forbid-only
```

- Docker stack build/recreate: passed.
- Frontend TypeScript: `npm run lint` passed.
- Frontend unit suite: `npm test -- --run` passed, 16 files / 32 tests.
- Backend suite: `pytest backend\tests` passed, 232 tests.
- Strict Playwright suite: 38 passed / 0 failed using desktop and mobile Chromium projects.
- Population pass uploaded 20 plastic-related PDFs and wrote `docs/qa/findings/population-run.md`.

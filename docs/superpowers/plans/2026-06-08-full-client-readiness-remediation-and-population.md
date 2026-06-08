# Full Client Readiness Remediation And Population Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove client-facing fake data and incomplete document actions, populate the local app with a realistic plastic-engineering data set using 20 downloaded public PDFs, and run a full QA sweep that exercises every visible workflow before presenting the app to a client.

**Architecture:** Make the React workspace render live API state on every operational surface, keep destructive configuration and schema changes behind admin authority, extend Playwright with a data-population pass plus browser action coverage, and add static guards that fail whenever fake demo values or raw JSON action links reappear in client-facing UI.

**Tech Stack:** Django REST backend, React/Vite frontend, TanStack Query, Vitest, Playwright Chromium desktop/mobile, PowerShell orchestration, public PDF fixtures from TAP Plastics and Plastic-Craft, markdown QA evidence under `docs/qa`.

---

## Worktree Contract

Worktree:

`C:\Users\user\.codex\worktrees\plastic-engineering-data-hub\client-readiness-qa-suite`

Branch:

`codex/client-readiness-qa-suite`

Current rule from the user:

No product code, test code, fixture code, or configuration files are edited until this plan is saved and reviewed. The only permitted edit before review is this plan document.

## Current System Analysis

### Critical Findings

1. `frontend/src/app/routes.tsx` renders a fake Home operational overview:
   - `recordQueue` is a static array.
   - Fake IDs and dates are displayed: `PE-1042`, `PE-1038`, `PE-1029`, `Today`, `Yesterday`, `Jun 4`.
   - Metric values are static: `128` open records, `17` pending review, `4` blocked tasks, `312` controlled documents.
   - Recent Record Activity rows are not linked to real records.

2. `frontend/src/features/documents/DocumentPanel.tsx` exposes raw API responses through client-facing buttons:
   - `Preview` links directly to `/api/documents/:id/preview/`, so the browser shows JSON.
   - `Audit` links directly to `/api/documents/:id/audit/`, so the browser shows JSON.
   - `Open` routes to `/documents/:id`, but the detail page only repeats metadata and does not provide a useful preview or audit surface.
   - `Download` correctly points to the file download API and should remain a direct download link.

3. QA coverage was too shallow for client readiness:
   - The prior suite downloaded one PDF, not 20.
   - It proved backend endpoints worked but did not click every document action in the UI.
   - It did not statically fail on fake UI metrics or demo records.
   - It did not populate enough supplier, raw material, product, specification, project, workflow, dashboard, folder, import, document, and audit data for realistic client review.

4. More client-facing hardcoded or inert elements need classification and coverage:
   - `frontend/src/features/records/RecordList.tsx` has a `Configure View` button with no behavior.
   - `frontend/src/features/records/RecordList.tsx` status filter lists `review` and `blocked`, while archive/release behavior now requires accurate live statuses including `archived`.
   - `frontend/src/features/dashboards/DashboardPage.tsx` displays `Direct Load` when no dashboard key is resolved.
   - `frontend/src/features/folders/FolderReviewInbox.tsx` has `User ID` input hint text. This may be acceptable as an input label/hint, but QA must verify the action is useful and validated.
   - `frontend/src/features/workflows/TaskInbox.tsx` displays a disabled `Find` button even though the search input filters as the user types.
   - `frontend/src/features/projects/ProjectList.tsx` is a direct-open form with a sample UUID input hint and no project list; this may be acceptable only if the project workload and seeded project detail routes are tested.
   - Route detail fallbacks in `frontend/src/app/routes.tsx` should be reviewed. A route may show an unavailable state, but it must not look like fake business data.

5. Existing route-health QA can pass without proving seeded detail behavior:
   - `frontend/e2e/client-readiness-operations.spec.ts` visits static paths such as `/documents/1` and `/tasks/folder-events/1`.
   - Client readiness tests must use IDs created during the run wherever the app supports detail routes.

6. Some required QA data cannot be created through current public app APIs:
   - Project routes expose workload, board, timeline, task move, and dependency behavior, not project creation.
   - Folder event routes expose list/detail/review actions, not arbitrary folder event creation.
   - Workflow task states are `open`, `done`, and `cancelled`; `blocked` is not a real workflow state.
   - QA population must therefore use a controlled local-only seed command for these objects, then exercise the real app UI/API after seeding.

7. Archive, record versions, and document revision upload are not sufficiently user-visible:
   - `frontend/src/features/records/RecordDetail.tsx` exposes Save and Release, but not Archive or Version History.
   - `frontend/src/features/documents/DocumentPanel.tsx` exposes new document upload and Release, but not Add Revision for an existing document.
   - Client readiness requires UI controls and browser-click tests for these workflows.

### Non-Bugs To Preserve

1. Backend starter configuration in `backend/apps/config_registry/fixtures/plastic_engineering_v1.json` is valid seed/config data, not fake UI state.
2. Test fixture strings inside `backend/tests`, `frontend/src/**/*.test.*`, and `frontend/e2e` are allowed when scoped to tests.
3. Form input hint text is allowed when it is clearly an input hint and not presented as real operational data.
4. Download links may continue to point directly to `/api/documents/:id/download/` because downloading a file is the expected browser behavior.

## Acceptance Criteria

- Home operational metrics are computed from live APIs, not static constants.
- Home recent record activity uses live records, shows the latest five relevant records, and every record code/title is clickable.
- Metric cards navigate to the appropriate workspace: records, tasks, or documents.
- Document `Open`, `Preview`, and `Audit` actions keep the user inside the app UI and do not display raw JSON.
- Document `Download` downloads a PDF and still works after the UI action changes.
- Record list status filters match real record states, including `archived`.
- No normal user can freely alter record/schema fields; admin/config-admin authority remains required.
- Records cannot be deleted through supported UI/API flows; they can be archived.
- Record archive and version history are visible and usable from the record detail UI.
- Record versions can be created and viewed through UI and API tests.
- Existing controlled documents can receive a new revision through the document detail UI.
- The QA data population pass downloads 20 public plastic-related PDFs and uploads them as controlled documents.
- QA data that current public APIs cannot create is produced by an explicit local-only Django seed command and then validated through normal app UI/API flows.
- If a public PDF source is temporarily unavailable, the run records that exact source failure and uses a generated reasonable PDF fallback only for completing downstream feature coverage.
- The final QA report contains a bug ledger, reproduction steps, fix status, and verification evidence.
- Full verification passes: backend tests, frontend lint, Vitest, Playwright desktop, Playwright mobile, static hardcoded-data audit, and document action UI tests.
- Final client-readiness verification has zero skipped Playwright tests.

## Public PDF Manifest

Create `frontend/e2e/support/plasticPdfManifest.ts` with these exact sources:

| # | Label | URL |
|---|---|---|
| 1 | Plastic-Craft Polycarbonate SDS | `https://plastic-craft.com/content/SDS/polycarbonate.pdf` |
| 2 | Plastic-Craft Polystyrene SDS | `https://plastic-craft.com/content/SDS/Polycarbonate/polystyrene.pdf` |
| 3 | ACRIFIX 2R 0190 SDS | `https://plastic-craft.com/content/SDS/ACRIFIX/ACRIFIX-2R-0190-US-v2.1.pdf` |
| 4 | ACRIFIX 2R 0190 Technical Information | `https://plastic-craft.com/content/TDS/ACRIFIX/ACRIFIX-2R-0190-Clear-Technical-Information.pdf` |
| 5 | ACRIFIX AC 1010 SDS | `https://plastic-craft.com/content/SDS/ACRIFIX-AC-1010-US-v2.2.pdf` |
| 6 | Primex ABS Data Sheet | `https://www.tapplastics.com/image/catalog/pdf/Primex%20ABS.pdf` |
| 7 | Acetal Technical Data | `https://www.tapplastics.com/image/pdf/Acetal_Technical_Data.pdf` |
| 8 | HDPE Typical Properties | `https://www.tapplastics.com/image/pdf/Typical_Properties_HDPE.pdf` |
| 9 | High Impact Polystyrene Technical Data | `https://www.tapplastics.com/image/pdf/Tech_Data-_Hi-Polystyrenes.pdf` |
| 10 | Polycarbonate AR Data Sheet | `https://www.tapplastics.com/image/pdf/Monogal-AR_Data_Sheet-04.19.171.pdf` |
| 11 | Polycarbonate Physical Properties | `https://www.tapplastics.com/image/pdf/Physical-Properties-Polycarbonate.pdf` |
| 12 | Polycarbonate GP Product Data | `https://www.tapplastics.com/image/pdf/Polycarbonate%20GP%20Product%20Data.pdf` |
| 13 | King CuttingBoard Physical Properties | `https://www.tapplastics.com/image/catalog/King-CuttingBoard-Physical-Properties.pdf` |
| 14 | King KPC HDPE Literature | `https://www.tapplastics.com/image/pdf/King-KPC-HDPE-Literature.pdf` |
| 15 | Komatex Foamed PVC Technical Values | `https://www.tapplastics.com/image/pdf/komatex_techvalues_07-3.pdf` |
| 16 | PVC Sheets Data | `https://www.tapplastics.com/image/pdf/PVC_Sheets_Data-2018.pdf` |
| 17 | Polypropylene Data | `https://www.tapplastics.com/image/pdf/Polypropylene_Data.pdf` |
| 18 | Vintec PVC Properties | `https://www.tapplastics.com/image/pdf/vintec_i_properties1.pdf` |
| 19 | SCIGRIP 4SC Technical Data | `https://www.tapplastics.com/image/pdf/4SC_TDS-1112.pdf` |
| 20 | Weld-On 4 Technical Data | `https://www.tapplastics.com/image/catalog/pdf/ips_weld-on_4_TDS_0120.pdf` |

## Realistic QA Data Set

Create a population pass that inserts a coherent plastic-engineering data set through the same APIs used by the app:

- 10 suppliers: resin distributor, compounder, sheet supplier, adhesive supplier, color masterbatch supplier, recycled resin supplier, lab partner, mold shop, packaging vendor, regulatory consultant.
- 20 raw materials: PC, ABS, HDPE, LDPE, PP, PA66, POM/acetal, PVC, PMMA, PS, HIPS, PETG, TPU, TPE, glass-filled nylon, regrind PC, recycled HDPE, UV-stabilized PP, flame-retardant PC/ABS, solvent cement.
- 15 products: molded enclosure, transparent guard, cable clip, fluid manifold, lab tray, appliance knob, outdoor bracket, packaging insert, medical device housing, conveyor guide, lens cover, welding fixture, battery spacer, valve body, recycled-content panel.
- 12 product specifications with tolerances, material family, target process, color, compliance, document requirements, release state.
- 8 relationships: product uses material, product has specification, supplier provides material, project references product, document supports specification.
- 4 projects: tooling transfer, regrind qualification, supplier change, controlled document cleanup.
- 16 workflow tasks spread across review, approval, overdue, blocked, and completed states.
- 6 folder events: new file, changed file, orphan document, ignored file, linked document, accepted file.
- 4 imports: dry-run success, dry-run validation failure, applied CSV import, repeat import update.
- 4 dashboards/saved views: active products, pending approvals, document extraction health, archived records.
- 20 controlled document uploads, one from each manifest PDF, linked to appropriate products/materials/specifications.

Every generated record title must include a run stamp such as `QA Client Seed 20260608T113000Z` so the data can be identified without deleting existing user data.

## Implementation Tasks

### Task 1: Plan Review Gate

**Files:**

- Modify only this plan until review is finished: `docs/superpowers/plans/2026-06-08-full-client-readiness-remediation-and-population.md`
- Create after review starts: `docs/qa/findings/full-client-readiness-plan-review.md`

- [ ] Self-review this plan for missing file paths, missing commands, vague acceptance criteria, and incomplete coverage.
- [ ] Dispatch a read-only reviewer subagent to inspect the repo and this plan.
- [ ] Ask the reviewer to identify missing workflows, unsafe assumptions, unreachable routes, data-population gaps, and tests that would pass without proving the user-visible behavior.
- [ ] Incorporate self-review findings: seeded IDs for route/detail tests, Task Inbox `Find` handling, and Project direct-open classification.
- [ ] Incorporate subagent findings: local-only seed command, Archive/Version UI, strict zero-skip E2E gate, Home metric/link correction, SavedViewBuilder status cleanup, browser-click document action proof, Add Revision UI, corrected commands, Home export removal, and QA report replacement.
- [ ] Save the reviewer findings to `docs/qa/findings/full-client-readiness-plan-review.md`.
- [ ] Revise this plan if the reviewer finds gaps.
- [ ] Start product implementation only after the review loop is complete.

### Task 2: Add Static Client-Facing Fake-Data Guards

**Files:**

- Create `frontend/src/app/clientReadinessStaticAudit.test.ts`
- Modify `frontend/src/app/App.test.tsx` only if route-level test utilities are needed.

Add a Vitest audit that scans client-facing source files and fails on known fake-state patterns. The allowed exceptions are tests, backend fixtures, and harmless form input hints.

Required assertions:

```ts
const bannedUiPatterns = [
  { file: "frontend/src/app/routes.tsx", pattern: /recordQueue/ },
  { file: "frontend/src/app/routes.tsx", pattern: /PE-1042|PE-1038|PE-1029/ },
  { file: "frontend/src/app/routes.tsx", pattern: /value="128"|value="312"|value="17"|value="4"/ },
  { file: "frontend/src/app/routes.tsx", pattern: /Today|Yesterday|Jun 4/ },
  { file: "frontend/src/features/documents/DocumentPanel.tsx", pattern: /href=\{document\.preview_url/ },
  { file: "frontend/src/features/documents/DocumentPanel.tsx", pattern: /href=\{document\.audit_url/ },
];
```

Additional scan requirements:

- Fail when a button or link labeled `Preview` opens a raw `/api/.../preview/` JSON route.
- Fail when a button or link labeled `Audit` opens a raw `/api/.../audit/` JSON route.
- Allow direct `/api/.../download/` links for file downloads.
- Record any newly discovered client-facing hardcoded business data in `docs/qa/findings/hardcoded-ui-audit.md`.

Verification command:

```powershell
npm --prefix frontend test -- --run src/app/clientReadinessStaticAudit.test.ts
```

### Task 3: Replace Home Demo State With Live Operational Data

**Files:**

- Modify `frontend/src/app/routes.tsx`
- Modify `frontend/src/app/App.test.tsx`
- Create `frontend/e2e/client-readiness-home.spec.ts`
- Update `docs/qa/client-readiness-qa-report.md`

Implementation details:

- Remove `RecordQueueItem`, `recordQueue`, and fake metric values from `routes.tsx`.
- Import `useQuery` from `@tanstack/react-query`.
- Import `apiGet` from `frontend/src/lib/api.ts`.
- Fetch:
  - `/records/` for records and recent activity.
  - `/workflow-tasks/?state=open` for pending review and overdue work counts.
  - `/documents/` for controlled document count.
- Compute metrics:
  - Open records: `records.filter(record => record.status !== "archived").length`.
  - Pending review: open workflow task count.
  - Overdue work: open workflow tasks where due date is before current date.
  - Controlled documents: document list length.
- Make each metric a `Link`:
  - Open records -> `/records`
  - Pending review -> `/tasks`
  - Overdue work -> `/tasks?due=overdue`
  - Controlled documents -> `/documents`
- Recent Record Activity:
  - Sort by `updated_at` descending.
  - Render maximum five rows.
  - Link record code/title to `/records/:id`.
  - Show a live empty state when there are no records.
  - Show loading and error states that do not contain fake business values.
- The Home export button must either perform a real export or be removed from Home for this release. If implemented, link it to the existing records export endpoint and add a test. If no suitable endpoint exists, remove it.

Vitest requirements:

- Mock `/api/records/`, `/api/workflow-tasks/?state=open`, and `/api/documents/`.
- Verify metric values match mocked array lengths.
- Verify no static values `128`, `312`, `PE-1042`, `Today`, or `Yesterday` render.
- Verify recent record rows are links to `/records/:id`.

Playwright requirements:

- Seed at least six records.
- Visit `/`.
- Verify the five newest records appear.
- Click a recent record row and assert the record detail opens.
- Click each metric card and assert navigation reaches the expected workspace.
- Assert metric labels and links match the exact population used for the count.

Verification commands:

```powershell
$env:PLAYWRIGHT_BASE_URL='http://localhost:5173'
$env:ALLOW_E2E_USER_SEEDING='true'
$env:E2E_PASSWORD='qa-password-12345'
npm --prefix frontend test -- --run src/app/App.test.tsx src/app/clientReadinessStaticAudit.test.ts
npm --prefix frontend exec playwright test e2e/client-readiness-home.spec.ts --project=chromium-desktop
```

### Task 4: Fix Document Open, Preview, And Audit User Experience

**Files:**

- Modify `frontend/src/features/documents/DocumentPanel.tsx`
- Modify `frontend/e2e/client-readiness-documents.spec.ts`
- Create or modify `frontend/src/features/documents/DocumentPanel.test.tsx`
- Update `docs/qa/client-readiness-qa-report.md`

Implementation details:

- Keep document title and `Open` as React Router links to `/documents/:id`.
- Change `Preview` from a raw API anchor to a React Router link:
  - `/documents/:id?view=preview`
- Change `Audit` from a raw API anchor to a React Router link:
  - `/documents/:id?view=audit`
- Keep `Download` as a direct API link:
  - `/api/documents/:id/download/`
- In `DocumentDetailPage`, read `view` from `useSearchParams`.
- Fetch document metadata from `/documents/:id/`.
- When `view=preview`, fetch `/documents/:id/preview/` and render:
  - extraction status
  - extracted text summary
  - material-property terms found
  - no raw JSON braces as the primary UI
- When `view=audit`, fetch `/documents/:id/audit/` and render:
  - action
  - actor/user
  - timestamp
  - revision/document identifiers
  - no raw JSON braces as the primary UI
- When `view` is missing, render useful document overview content and action tabs/buttons for overview, preview, audit, and download.
- Add an Add Revision control on document detail:
  - accept a file and revision label.
  - post multipart data to `/documents/:id/revisions/`.
  - refresh document metadata after upload.
  - show extraction state for the new revision.
- Handle loading, empty, and error states with human-readable UI.

Unit test requirements:

- Render a document item and assert `Preview` href is `/documents/:id?view=preview`.
- Assert `Audit` href is `/documents/:id?view=audit`.
- Assert `Download` href remains `/api/documents/:id/download/`.
- Mock preview and audit API responses and assert detail page renders formatted UI.
- Mock add-revision multipart submission and assert the detail view refreshes metadata.

Playwright requirements:

- Upload one of the 20 PDFs.
- Visit `/documents`.
- Click `Open` from the document list; verify metadata page opens and app navigation remains visible.
- Click `Preview` from the document list; verify the URL is `/documents/:id?view=preview`, extracted text is visible, app navigation remains visible, and the page body is not raw JSON.
- Click `Audit` from the document list; verify the URL is `/documents/:id?view=audit`, audit rows are visible, app navigation remains visible, and the page body is not raw JSON.
- Add revision B through the document detail UI and verify it appears in the revision history.
- Click `Download`; verify downloaded bytes start with `%PDF`.

Verification commands:

```powershell
$env:PLAYWRIGHT_BASE_URL='http://localhost:5173'
$env:ALLOW_E2E_USER_SEEDING='true'
$env:E2E_PASSWORD='qa-password-12345'
npm --prefix frontend test -- --run src/features/documents/DocumentPanel.test.tsx src/app/clientReadinessStaticAudit.test.ts
npm --prefix frontend exec playwright test e2e/client-readiness-documents.spec.ts --project=chromium-desktop
```

### Task 5: Correct Record Filters And Inert Client Actions

**Files:**

- Modify `frontend/src/features/records/RecordList.tsx`
- Modify `frontend/src/features/records/RecordDetail.tsx`
- Modify `frontend/src/features/dashboards/SavedViewBuilder.tsx`
- Modify `frontend/src/features/dashboards/DashboardPage.tsx`
- Modify `frontend/src/features/folders/FolderReviewInbox.tsx` only if browser testing proves an action is inert or unclear.
- Modify `frontend/src/app/routes.tsx` route fallback states if they read like fake business data.
- Update `docs/qa/findings/hardcoded-ui-audit.md`

Implementation details:

- Update Record status filter options to match real supported states:
  - `draft`
  - `released`
  - `archived`
- If the backend exposes valid statuses through config or an enum endpoint, derive filter options from that source instead of hardcoding.
- Apply the same status options to `SavedViewBuilder`.
- Add Archive and Version History controls to `RecordDetail`:
  - Archive is visible only when the current user has the needed authority.
  - Archive calls `/records/:id/archive/`, shows a confirmation step, refreshes the record, and never deletes the row.
  - Version History lists `/records/:id/versions/`.
  - Create Version calls `/records/:id/versions/` and adds a new immutable snapshot.
- Make `Configure View` in `RecordList` perform a real action:
  - preferred: open saved view/dashboard controls that already exist on the page.
  - acceptable for this release: remove the button if no real configuration UI exists.
- Review dashboard `Direct Load` display:
  - If it is diagnostic text, replace it with a user-facing state such as `No dashboard selected`.
  - If direct dashboard loading is real, add a test proving it works with a seeded dashboard key.
- Review folder assignment UI:
  - Keep `User ID` only if it is a working, validated field.
  - Add validation feedback for invalid IDs if missing.
- Review Task Inbox search UI:
  - Make the `Find` button run the same search/filter action as pressing Enter, or remove the disabled button and rely on live filtering.
  - Add a test that entering text in `Search tasks` changes the visible task set.
- Review Project workspace direct-open UI:
  - Keep direct UUID open only if seeded project IDs are available in QA and validation feedback is clear.
  - If a project listing endpoint exists, replace the direct-only workflow with a live list plus direct-open fallback.

Test requirements:

- Assert archived records can be filtered in the UI.
- Assert unsupported statuses are not shown as filter choices unless the backend supports them.
- Assert Saved View status choices include `archived` and exclude unsupported `blocked`/`review` values.
- Assert a user can create a record version and view it in the RecordDetail UI.
- Assert a permitted user can archive a record from RecordDetail, and a normal user without privilege cannot.
- Assert no delete button or DELETE flow exists for records.
- Assert any visible button on Records, Documents, Home, Dashboards, Tasks, Imports, Audit, Projects, Search, and Admin either performs a real action, navigates, downloads a file, or is removed.
- Assert disabled visible controls are either intentionally disabled because prerequisites are missing or are removed from the client surface.

Verification commands:

```powershell
npm --prefix frontend test -- --run
$env:PLAYWRIGHT_BASE_URL='http://localhost:5173'
$env:ALLOW_E2E_USER_SEEDING='true'
$env:E2E_PASSWORD='qa-password-12345'
npm --prefix frontend exec playwright test e2e/client-readiness-operations.spec.ts --project=chromium-desktop
```

### Task 6: Build The 20-PDF Population Pass

**Files:**

- Create `frontend/e2e/support/plasticPdfManifest.ts`
- Modify `frontend/e2e/support/qaApi.ts`
- Create `frontend/e2e/support/clientReadinessSeed.ts`
- Create `backend/apps/api/management/__init__.py`
- Create `backend/apps/api/management/commands/__init__.py`
- Create `backend/apps/api/management/commands/seed_client_readiness_demo.py`
- Create `backend/tests/api/test_seed_client_readiness_demo.py`
- Create `frontend/e2e/client-readiness-population.spec.ts`
- Update `docs/qa/client-readiness-qa-report.md`
- Create `docs/qa/findings/population-run.md`

Implementation details:

- Add `downloadPlasticPdfSet(request)` to download all 20 PDFs.
- Save files under `frontend/test-results/qa-assets/plastic-pdf-set/`.
- Save SHA-256 checksum files next to each PDF.
- Validate every downloaded document:
  - HTTP status OK.
  - body length greater than 1,000 bytes.
  - first four bytes are `%PDF`.
  - source URL, status, byte count, and checksum are recorded.
- For temporary source failures, generate a synthetic but reasonable PDF using a deterministic filename and content. Mark the source as `generated_fallback` in `docs/qa/findings/population-run.md`.
- Use app APIs to create records, relationships, imports, saved views, dashboards, and document uploads wherever the public API supports creation.
- Use `seed_client_readiness_demo` for local-only data that current APIs cannot create: projects, project tasks, workflow tasks with due dates, managed folders, and folder change events.
- The seed command must refuse to run unless one of these is true:
  - `settings.DEBUG` is true and the database host is local/private.
  - `ALLOW_CLIENT_READINESS_SEED=true` is set.
- The seed command must write a JSON manifest containing run id, created object IDs, and counts.
- The seed command must not delete existing user data.
- Keep the existing local-target mutation gate from `qaApi.ts`.
- Use unique run stamps to avoid overwriting user data.
- Archive only QA-created records when archive behavior must be tested. Do not delete records.

Seed helper shape:

```ts
export type ClientReadinessSeedResult = {
  runId: string;
  suppliers: RecordPayload[];
  rawMaterials: RecordPayload[];
  products: RecordPayload[];
  productSpecs: RecordPayload[];
  documents: DocumentPayload[];
  projects: Array<{ id: string; name: string }>;
  tasks: Array<{ id: number; title: string }>;
  pdfs: Array<{ label: string; url: string; path: string; sha256: string; fallback: boolean }>;
};
```

Population spec requirements:

- Authenticate as engineer, config admin, and system admin where needed.
- Run the local-only seed command before browser assertions when `QA_POPULATE_FULL_DATASET=true`.
- Create the data set listed in the `Realistic QA Data Set` section.
- Upload each of the 20 PDFs as a controlled document.
- Verify `/documents` lists at least the 20 uploaded QA documents.
- Verify `/records` can find at least one record from each object type.
- Verify `/search` finds a material term from document extraction, such as polycarbonate, ABS, HDPE, PVC, or polypropylene.
- Verify `/audit` shows activity for created records and documents.
- Verify `/dashboards` and saved views reflect populated data.
- Verify project, folder event, and workflow task route checks use IDs from the seed manifest.

Verification command:

```powershell
$env:PLAYWRIGHT_BASE_URL='http://localhost:5173'
$env:ALLOW_E2E_USER_SEEDING='true'
$env:E2E_PASSWORD='qa-password-12345'
$env:QA_POPULATE_FULL_DATASET='true'
$env:ALLOW_CLIENT_READINESS_SEED='true'
npm --prefix frontend exec playwright test e2e/client-readiness-population.spec.ts --project=chromium-desktop --forbid-only
```

### Task 7: Full Feature QA Sweep

**Files:**

- Modify `frontend/e2e/client-readiness-records.spec.ts`
- Modify `frontend/e2e/client-readiness-documents.spec.ts`
- Modify `frontend/e2e/client-readiness-operations.spec.ts`
- Create `frontend/e2e/client-readiness-home.spec.ts`
- Create `frontend/e2e/client-readiness-action-sweep.spec.ts`
- Update `docs/qa/client-readiness-qa-report.md`
- Create `docs/qa/findings/action-sweep.md`

Action sweep matrix:

| Area | Must exercise |
|---|---|
| Home | Live metrics, recent record links, new record navigation, export if present |
| Records | list, search, object type filter, status filter, saved view, dashboard filter, create, edit, release, archive, version history, no delete |
| Admin | field/schema edit is admin-only, destructive field changes are protected, normal users blocked |
| Documents | upload, open, preview, audit, download, release revision, add revision, released revision cannot be replaced |
| Projects | list, detail, board, move task, timeline, dependencies, invalid dependency rejection |
| Imports | CSV dry run, validation error, apply import, repeat update |
| Search | record result, document text result, detail navigation |
| Dashboards | saved view results, dashboard widgets, seeded dashboard route |
| Audit | record, document, relationship, import, backup, and config events |
| Tasks | inbox, workflow state, folder review inbox, accept, ignore, assign, link document |
| Backups | system admin can create, non-system user blocked, missing `pg_dump` returns JSON error |
| Access | engineer, config admin, system admin, read-only boundaries |

Browser assertions:

- No route may show `JSON.parse: unexpected character`, `Workload failed`, a raw Django/HTML error page, or raw JSON when reached through a normal app button.
- Every visible action button either changes UI state, navigates, opens a modal/panel, downloads a file, or gives a controlled disabled/error state.
- Every download must validate content type or file signature.
- Every action that mutates data must leave an audit event.
- Detail-route checks must use seeded IDs from the current run instead of static IDs such as `/documents/1`, `/projects/1`, `/tasks/folder-events/1`, or `/records/1`.
- Playwright client-readiness runs must fail when any test is skipped in strict readiness mode.

Verification command:

```powershell
npm --prefix frontend exec playwright test --project=chromium-desktop
npm --prefix frontend exec playwright test --project=chromium-mobile
```

### Task 8: Documentation And Bug Ledger

**Files:**

- Modify `docs/qa/client-readiness-qa-report.md`
- Create or modify `docs/qa/findings/hardcoded-ui-audit.md`
- Create or modify `docs/qa/findings/document-actions.md`
- Create or modify `docs/qa/findings/population-run.md`
- Create or modify `docs/qa/findings/action-sweep.md`
- Create or modify `docs/qa/findings/final-verification.md`

Report requirements:

- List every bug found, with severity, area, reproduction, expected behavior, actual behavior, fix status, and verification command.
- Include a section for hardcoded/fake UI elements found and removed.
- Include a section for 20-PDF population results with source URL, checksum, linked record, document id, extraction status, and fallback flag.
- Replace stale prior summary claims such as one-PDF coverage or older Playwright pass counts with the latest verified run.
- Include a section for features tested and features not available by design.
- Include remaining risks: production SSO/TLS, company network file shares, restore drills, performance/load, browser matrix outside Chromium if not tested.

### Task 9: Final Verification Gate

**Files:**

- Modify files only as required by prior tasks.
- Update `docs/qa/findings/final-verification.md` with command outputs and dates.

Run these commands from the worktree:

```powershell
git status --short --branch
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
npm --prefix frontend run lint
npm --prefix frontend test -- --run
& '.\backend\.venv\Scripts\python.exe' -m pytest backend\tests
$env:PLAYWRIGHT_BASE_URL='http://localhost:5173'
$env:ALLOW_E2E_USER_SEEDING='true'
$env:E2E_PASSWORD='qa-password-12345'
$env:ALLOW_CLIENT_READINESS_SEED='true'
& '.\backend\.venv\Scripts\python.exe' backend\manage.py seed_client_readiness_demo --run-id "manual-readiness-$(Get-Date -Format yyyyMMddHHmmss)"
$env:PLAYWRIGHT_BASE_URL='http://localhost:5173'
$env:ALLOW_E2E_USER_SEEDING='true'
$env:E2E_PASSWORD='qa-password-12345'
$env:QA_POPULATE_FULL_DATASET='true'
npm --prefix frontend exec playwright test --project=chromium-desktop --forbid-only
npm --prefix frontend exec playwright test --project=chromium-mobile --forbid-only
git status --short --branch
```

Pass criteria:

- Lint passes.
- Vitest passes.
- Backend tests pass.
- Playwright desktop passes.
- Playwright mobile passes.
- Playwright reports zero skipped client-readiness tests.
- Static hardcoded UI audit passes.
- 20-PDF population either downloads 20 PDFs or records exact temporary source failures and deterministic generated fallbacks.
- No product-code edits remain undocumented in the QA report.

## Implementation Order

1. Complete Task 1 review gate.
2. Add failing static and UI tests for the known defects.
3. Fix Home live data and clickable records.
4. Fix document Open/Preview/Audit UI.
5. Add document Add Revision UI.
6. Add Record Archive and Version History UI.
7. Fix status filters, SavedViewBuilder statuses, and inert client actions.
8. Build and run the local-only seed command and 20-PDF population pass.
9. Run the full feature QA sweep.
10. Replace the QA report and findings files with current evidence.
11. Run final verification.
12. Commit and push only after all verification is complete, unless a blocker is documented.

## Subagent Review Request

Ask the reviewer to answer these points:

- Does the plan cover every client-visible feature currently exposed by navigation?
- Does the plan prevent fake Home metrics and fake Recent Record Activity from returning?
- Does the plan prove document actions through browser clicks rather than backend-only checks?
- Does the plan populate enough data for a realistic client demo?
- Does the plan avoid direct database writes during QA population?
- Does the plan preserve admin-only authority for field/schema changes?
- Does the plan protect existing user data by using run-stamped QA records and archive-only cleanup?
- Are any commands, files, acceptance criteria, or data expectations missing?

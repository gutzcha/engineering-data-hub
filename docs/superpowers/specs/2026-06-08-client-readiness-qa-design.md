# Client Readiness QA Design

## Objective

Build and run a client-readiness QA program for the Plastic Engineering Data Hub. The program must verify the current app end to end, prove dangerous operations are constrained, exercise realistic plastic-engineering data and documents, and produce a client-facing bug ledger with evidence.

## Current Product Surface

The app exposes these user-visible workspaces:

- Home dashboard at `/`
- Records at `/records`, `/records/new`, and `/records/:recordId`
- Projects at `/projects` and `/projects/:projectId`
- Imports at `/imports`
- Documents at `/documents` and `/documents/:documentId`
- Search at `/search`
- Dashboards at `/dashboards`
- Audit at `/audit`
- Tasks and folder review at `/tasks`, `/tasks/folder-events`, and `/tasks/folder-events/:eventId`
- Admin configuration at `/admin`

The app exposes these backend domains:

- Authentication, CSRF, session state, and permission inspection
- Configuration registry with active config, history, drafts, validation, and publishing
- Records with create, list, detail, patch, release, graph, audit, and managed-folder generation
- Documents with create, revisions, revision release, preview, download, and audit
- Relationships with create and delete
- Imports, folder scanning, folder-link acceptance, and Excel exports
- Folder review event accept, ignore, assign, and link-document actions
- Workflow tasks and record workflow transitions
- Search
- Saved views and dashboards
- Project workload, board, timeline, task moves, and dependencies
- Backup creation and inspection
- Audit event lists and object-specific audit timelines

## Requirements Interpreted As QA Gates

Records must be creatable through the UI and API.

Record deletion must not be possible through UI or API. API DELETE must return a controlled 405 or 403-class response, and no destructive delete control should be visible in the record UI.

Archiving must be possible instead of deletion. Because current `Record.Status` only contains `draft` and `released`, this is expected to fail and must be reported as a product gap unless implementation is added before final execution.

Record versions must be possible. Because current code only has document revisions and record audit snapshots, this is expected to fail and must be reported as a product gap unless implementation is added before final execution.

Document revisions must work for controlled document lifecycle. Existing code supports document revisions, released revision protection, preview, download, extraction, and audit; QA must exercise those with a real plastic-engineering PDF.

Admin-only authority must protect schema and field changes. Configuration Admins can edit non-destructive configuration drafts. Destructive field removals require System Admin confirmation. Normal users must not be able to create, update, validate, or publish configuration drafts.

All visible app routes must load without the JSON parsing workload failure that was previously seen on Records.

## Test Strategy

The QA suite will be a Playwright-driven hybrid suite:

- Browser tests prove real navigation, forms, buttons, file inputs, route reloads, and visible UI states.
- API calls through Playwright's `APIRequestContext` create deterministic fixtures quickly and verify method-level security.
- Backend pytest coverage remains the source of truth for deeper model and serializer behavior where browser tests would be brittle.
- The final QA report records every observed defect, product gap, flaky area, skipped prerequisite, and evidence path.

The suite will not mutate production data. It runs against a local server using timestamped test data names prefixed with `QA-` or `PW-`, and it writes downloaded fixture files under ignored `frontend/test-results/qa-assets/`.

Mutating tests must fail closed unless the base URL is a local target (`localhost`, `127.0.0.1`, `plastic-hub.local`, `backend`, or a Docker/private host) or `QA_ALLOW_NON_LOCAL_MUTATION=true` is explicitly set. This prevents accidental QA writes against a customer or production server.

## Real Document Fixture

The external document upload test will download Plastic-Craft's public polycarbonate technical data sheet:

`https://plastic-craft.com/content/SDS/polycarbonate.pdf`

The document is a small two-page polycarbonate technical data sheet that includes material properties such as density, tensile strength, flexural modulus, heat deflection temperature, and flammability rating. The QA test will download it at runtime, upload it as a document revision, confirm extraction/preview text contains plastic-domain terms, release the revision, download it back, and verify the downloaded bytes are non-empty.

## Roles And Permission Matrix

The suite assumes these logical roles:

- System Admin: superuser-equivalent, can publish destructive configuration changes with explicit confirmation.
- Configuration Admin: can create and validate config drafts, but cannot publish destructive changes.
- Engineering User: can create/edit/release permitted records and documents, but cannot edit configuration.
- Read-only or restricted user: can view permitted records only, and must not see or mutate forbidden object types.

When the running environment cannot seed these users automatically, the suite must skip only the dependent tests with a precise message. It must not report skipped prerequisites as passed behavior.

## Coverage Matrix

### Authentication And Session

- CSRF token can be fetched.
- Login succeeds with seeded QA credentials.
- `/api/accounts/me/` returns the logged-in user.
- Logout ends the session.
- Unauthenticated protected APIs fail predictably.

### Records

- Record list loads as valid JSON and renders in UI.
- New Record button opens `/records/new`.
- Product, supplier, raw material, and product spec records can be created with plastic-domain data.
- Required-field validation appears for incomplete records.
- Manual record codes are blocked for non-admins.
- Object type, code, and status cannot be changed through generic PATCH.
- Record release uses the release endpoint.
- DELETE is unavailable and no delete UI is visible.
- Archive is available and audited; if absent, log a critical product gap.
- Record version creation and browsing are available; if absent, log a critical product gap.
- Record audit captures created, updated, released, relationship, folder, document, and workflow events.

### Documents

- Document list loads.
- Real polycarbonate PDF downloads from the internet into ignored test artifacts.
- Initial document revision upload succeeds against a record.
- Extraction status and preview text are visible.
- Download returns a non-empty PDF response.
- Releasing a revision changes revision/document state.
- Uploading a second revision with a new label succeeds.
- Replacing a released revision with the same label is blocked.
- Document DELETE and PATCH are unavailable.

### Relationships And Graph

- Product-to-material and product-to-spec relationships can be created.
- Invalid relationship targets are rejected.
- Graph endpoint returns nodes and edges visible to the user.
- Relationship deletion is permission-gated and audited.

### Admin Configuration

- Active config loads for authenticated users.
- Normal users cannot access config history or draft mutation endpoints.
- Configuration Admin can create, update, and validate a draft.
- Configuration Admin cannot publish destructive field removals.
- System Admin can publish destructive changes only with `confirm_breaking_changes: true`.
- Existing records retain their JSON data when a field is removed from future config, and the removal is captured as a breaking change.

### Imports And Exports

- Import wizard loads active config.
- CSV/XLSX upload creates an import job.
- Dry run reports mapped rows and validation errors.
- Apply creates records only after dry run.
- Folder scan identifies candidate legacy folders.
- Folder-link acceptance creates or connects managed folders.
- Records, audit, and project-status exports download as XLSX files.

### Projects And Workflows

- Project workload page loads.
- Project board and timeline load for a seeded project.
- Moving a project task persists.
- Adding dependencies works and invalid cycles fail.
- Workflow state loads for a record.
- Allowed transitions create tasks and move state.
- Completing tasks updates task inbox and workflow status.

### Search, Dashboards, Audit, Backups

- Search returns records, documents, and folder events after indexing. Project search is treated as a product-specific gate: current code does not reliably expose project hits to non-admin users, so the suite must either seed/admin-check that path or report it as a gap.
- Search respects permissions.
- Dashboards and saved views load and return result rows.
- Audit timeline loads and includes newly generated QA events.
- Backup creation and detail endpoints work for admin users.

### Browser And UI Health

- All navigation items route without console errors.
- Direct route reloads load the React app for every app route. `/admin` is high risk because Vite currently proxies `/admin` to Django admin.
- Desktop and mobile viewports render without obvious overlap on key pages.
- Primary actions have accessible names and stable enabled/disabled states.

## Bug Severity Rubric

- Critical: data loss, unauthorized destructive mutation, record deletion possible, archive/version requirement absent, client-blocking route failure, upload/download corrupts documents.
- High: permission leak, workflow dead end, import applies invalid rows, released revision can be overwritten, route reload broken.
- Medium: missing validation, inaccurate audit, incomplete search/dashboard results, poor error copy, responsive layout defect.
- Low: cosmetic inconsistency, minor missing loading state, non-blocking wording issue.

## Deliverables

- QA design document: this file.
- Implementation plan: `docs/superpowers/plans/2026-06-08-client-readiness-qa-suite.md`.
- Automated QA files under `frontend/e2e/`.
- A client-facing QA report under `docs/qa/client-readiness-qa-report.md`.
- Subagent finding notes under `docs/qa/findings/`.
- Test artifacts under ignored `frontend/test-results/`.

## Self Review

- No placeholders remain.
- The plan treats absent archive and record-version support as explicit QA failures rather than assumptions.
- The suite is scoped to testing and documentation; feature implementation is only considered if a QA failure blocks basic test execution.
- The external document source is concrete and public.
- Dangerous schema changes are tested through role and confirmation gates.

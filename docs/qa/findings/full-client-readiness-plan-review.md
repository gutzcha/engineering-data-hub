# Full Client Readiness Plan Review

Date: 2026-06-08

Reviewer: Archimedes, read-only subagent

Scope:

- `docs/superpowers/plans/2026-06-08-full-client-readiness-remediation-and-population.md`
- `frontend/src/app/routes.tsx`
- `frontend/src/features/documents/DocumentPanel.tsx`
- `frontend/src/features/records/RecordDetail.tsx`
- `frontend/src/features/records/RecordList.tsx`
- `frontend/src/features/dashboards/SavedViewBuilder.tsx`
- `frontend/e2e/support/qaApi.ts`
- `frontend/e2e/client-readiness-*.spec.ts`
- backend project, folder, workflow, document, record, import, and report routes

## Required Plan Changes

### P0: QA Population Cannot Be API-Only With Current Endpoints

The plan required creating projects, project tasks, workflow task states, and folder events through app APIs, but current APIs do not support all of those create operations.

Evidence:

- `backend/apps/projects/urls.py` exposes project board/timeline/move/dependency behavior, not general project creation.
- `backend/apps/folders/views.py` exposes folder event review behavior, not arbitrary event creation.
- `backend/apps/workflows/models.py` supports workflow states `open`, `done`, and `cancelled`; there is no real `blocked` workflow state.

Plan correction:

- Add a local-only QA seed command or equivalent controlled local-only seed mechanism for non-publicly-creatable domain objects.
- Keep browser/API tests exercising the real app after seed data exists.
- Keep mutation guarded to local QA targets only.

### P0: Archive And Version Must Be User-Visible, Not API-Only

The plan included archive and version acceptance criteria, but the React record detail page only exposes Save and Release.

Evidence:

- Backend endpoints exist in `backend/apps/records/views.py`.
- `frontend/src/features/records/RecordDetail.tsx` does not expose Archive or Version History controls.
- Existing Playwright coverage uses backend/API behavior and does not prove a user can archive or inspect versions in the UI.

Plan correction:

- Add Archive and Version History UI to record detail.
- Add Vitest and Playwright tests that click those controls.

### P0: Skipped E2E Tests Must Fail Final Readiness

Existing Playwright specs skip when the stack or QA users are unavailable. That is acceptable for local developer convenience, but not for client-readiness certification.

Evidence:

- Existing specs call `test.skip` when health checks or QA user setup fail.

Plan correction:

- Add a strict readiness mode.
- Final verification must fail on skipped client-readiness tests.
- Every Playwright command must set the required environment variables or run a preflight that hard-fails first.

### P1: Home Metrics Need Endpoint And Link Corrections

The plan counted blocked tasks from `/workflow-tasks/?state=open`, but the endpoint exact-filters state. The plan also counted all non-archived records but linked Open Records to only `status=draft`.

Plan correction:

- Use open workflow tasks for Pending Review.
- Use overdue open tasks for Blocked/Overdue Work, or fetch all states if backend support is added.
- Link Open Records to `/records`, not a narrower status filter unless the count uses that same filter.

### P1: Status Cleanup Must Include Saved Views

The plan corrected `RecordList`, but `SavedViewBuilder` also offers unsupported statuses and omits `archived`.

Plan correction:

- Include `frontend/src/features/dashboards/SavedViewBuilder.tsx` in status cleanup.
- Test archived saved-view filtering.

### P1: Document Action Tests Must Prove Browser Behavior

Existing document E2E verifies preview through the API. It does not prove that clicking `Preview` or `Audit` keeps the user in the app.

Plan correction:

- Click `Open`, `Preview`, and `Audit` from the document list.
- Assert the URL is `/documents/:id` or `/documents/:id?view=...`.
- Assert app navigation remains visible.
- Assert formatted UI labels are visible.
- Assert the body is not raw JSON.

### P1: Add Revision Is In Scope But Has No UI Plan

The QA matrix includes adding a document revision, but `DocumentPanel` currently exposes new document upload and release, not adding a revision to an existing document.

Plan correction:

- Add document revision upload UI in document detail or explicitly classify add-revision as API-only.
- For client readiness, implement the UI and test it.

### P1: Verification Commands Need Worktree-Correct Paths

Some commands use `npm --prefix frontend` while also passing `frontend/src/...` paths, and the backend pytest command points at another worktree path.

Plan correction:

- Use `src/...` paths when running Vitest through `npm --prefix frontend`.
- Use the current worktree backend venv when available.
- Add explicit stack start/rebuild commands before Playwright.

### P2: Home Export Must Not Remain Inert

The Home export button is inert and the existing export endpoint requires an object type.

Plan correction:

- Remove the Home export button for this release, or implement an explicit object-type export with download verification.
- The conservative release choice is to remove it.

### P2: QA Report Must Supersede Stale Evidence

The existing QA report says one PDF and 34 Playwright checks. That will become stale after this larger sweep.

Plan correction:

- Replace or supersede the old summary, not merely append new content.
- The report must name the latest verification run and its artifacts.

## Reviewer Conclusion

The plan is directionally correct but was not implementation-ready until these corrections were added. The biggest risks were API contract mismatch in population, API-only coverage for user-visible archive/version/document revision behavior, and Playwright skips hiding readiness failures.


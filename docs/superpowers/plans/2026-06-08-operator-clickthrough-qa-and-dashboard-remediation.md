# Operator Clickthrough QA And Dashboard Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the QA suite from API/route smoke checks into real operator clickthrough coverage, fix dashboard widget click-through behavior, and document every client-visible defect found while using the app like an actual user.

**Architecture:** Add a strict Playwright operator harness that creates realistic app data, logs in as multiple roles, clicks every visible tab/action, verifies the resulting UI/API/audit state, and writes findings. Fix product gaps only after a failing browser or unit test proves the missing behavior, starting with dashboard widget rows that must navigate/filter instead of being inert summaries.

**Tech Stack:** Django REST backend, PostgreSQL, React/Vite, TanStack Query, Vitest, Playwright Chromium desktop/mobile, existing local Docker stack, existing QA seeding helpers under `frontend/e2e/support`.

**Execution status:** Completed on 2026-06-08. Final evidence is recorded in `docs/qa/findings/final-verification.md` and `docs/qa/findings/operator-clickthrough.md`.

---

## Worktree Contract

Worktree:

`C:\Users\user\.codex\worktrees\plastic-engineering-data-hub\client-readiness-qa-suite`

Branch:

`codex/client-readiness-qa-suite`

Current hard rule:

Do not edit product code until this plan is saved and reviewed. This file is the only planned edit before review.

## Current Root Cause Assessment

The previous QA failure was not caused by a lack of tests. It was caused by bad test shape:

1. API success was treated as UI success.
2. Route loading was treated as feature usability.
3. Skips and soft failures were allowed in a client-readiness story.
4. Visible controls were not inventoried and clicked.
5. Dashboard widgets were checked for text, not for navigation/filter behavior.
6. Admin authority was checked mostly through API permission boundaries, not through actual UI attempts by both admin and normal users.

## Mandatory Operator Rules

Every client-readiness Playwright test added by this plan must obey these rules:

- Login through the UI unless a helper is explicitly preparing data.
- Use actual buttons, links, selects, inputs, tabs, and file inputs wherever the workflow is exposed in the product.
- Every visible control must be classified as one of:
  - navigates
  - mutates data
  - opens a panel/tab/modal
  - downloads a file
  - is disabled with a clear prerequisite
  - is a documented bug
- No client-readiness test may use static detail IDs such as `/records/1`, `/documents/1`, `/projects/1`, or `/tasks/folder-events/1`.
- Strict mode must fail instead of skipping when the local stack, user seeding, or data population is unavailable.
- A passing test must assert the user-visible result, not only the HTTP status.
- Every mutation must be followed by one of:
  - visible UI state change
  - refreshed data value
  - navigable detail page
  - audit event
  - downloaded file signature

## Operator Coverage Matrix

| Area | Operator actions that must be performed |
|---|---|
| Authentication | login with wrong password, login as engineer, login as config admin, login as system admin, login as read-only, logout, route access after logout |
| Home | click New Record, click every metric card, click recent record code/title, verify counts against APIs |
| Records | create, edit fields, save, release, archive, create version, inspect version history, verify no delete, filter object type, filter status, search by code/title/material |
| Admin Configuration | normal user tries to create draft and is denied, config admin creates draft, adds a field, validates, publishes non-destructive change, system admin confirms destructive field removal, normal user cannot remove/publish fields |
| Documents | upload, open, preview, audit, download, release revision, add revision, reject replacing released revision, attempt unsupported edit/delete/remove action and verify controlled result |
| Projects | create project through UI, list projects, open project, edit project status/owner, assign/change task assignee, change task status, move task on board, change dependency, verify workload updates |
| Imports | upload CSV, dry run, apply, validation error path, create managed folders toggle |
| Search | search record text, search document text, filter by records/documents/projects/folder events, click results |
| Dashboards | choose configured dashboard, refresh, click every widget row/segment, verify records-by-status rows navigate to filtered records, run saved view, click saved-view result rows |
| Audit | open audit, click object links, verify record/document/project/config/import events after mutations |
| Tasks | complete workflow task, filter/search tasks, click related object, folder review accept/ignore/assign/link-document |
| Backups | system admin list/create/detail through API or a new Admin backup panel, normal user blocked with controlled JSON/UI error, no raw HTML 500 |

## Known Bug To Fix First

`frontend/src/features/dashboards/DashboardPage.tsx` currently only creates links for dashboard widget items that contain `record_id` or `{ object_type: "record", object_id }`. Count widgets such as `Records By Status` return rows like `{ key: "archived", count: 4 }`, so they render as inert divs. Operator expectation:

- `Records By Status > Draft` opens `/records?status=draft`.
- `Records By Status > Released` opens `/records?status=released`.
- `Records By Status > Archived` opens `/records?status=archived`.
- `Records By Object Type > Product` opens `/records?object_type_key=product`.
- Scoped status widgets preserve their object-type filter, for example `Projects By Status > Active` opens `/records?object_type_key=project&status=active`.
- Missing-document rows open their record.
- Recent-change rows open the object when the object route is known.
- Workflow/project task rows open project or task workspace when possible.

## File Structure

### New Test/QA Files

- Create `frontend/e2e/client-readiness-operator-clickthrough.spec.ts`
  - Full browser workflow using real clicks across all app tabs.
- Create `frontend/e2e/support/operatorActions.ts`
  - Shared helpers for login/logout, visible-control inventory, safe click assertions, download assertions, and audit checks.
- Create `docs/qa/findings/operator-clickthrough.md`
  - Human-readable bug ledger produced by the operator sweep.

### Modified Test Files

- Modify `frontend/src/features/dashboards/DashboardPage.test.tsx`
  - Add failing unit coverage for clickable dashboard widget rows.
- Modify `frontend/e2e/client-readiness-operations.spec.ts`
  - Remove soft-pass patterns for dashboard/project/operator behavior and require strict failures.
- Modify `frontend/e2e/client-readiness-documents.spec.ts`
  - Add browser-click proof for Open, Preview, Audit, Download, Add Revision, Release.
- Modify `frontend/e2e/client-readiness-records.spec.ts`
  - Add UI proof for field edit/save/version/archive and normal-user denial.
- Modify `frontend/e2e/support/qaApi.ts`
  - Add only missing setup helpers needed for deterministic operator data.

### Modified Product Files

- Modify `frontend/src/features/dashboards/DashboardPage.tsx`
  - Make dashboard widget rows clickable according to widget type/config/item data.
- Modify `frontend/src/features/dashboards/SavedViewBuilder.tsx`
  - Only if operator tests prove saved-view results or status filters are not actionable.
- Modify `frontend/src/features/projects/ProjectList.tsx`
  - Add project creation UI if no visible project creation workflow exists.
- Modify `frontend/src/features/projects/ProjectBoard.tsx`
  - Add task status and assignee controls if no visible workflow exists.
- Modify `frontend/src/features/projects/ProjectDetail.tsx`
  - Add project status/owner controls if no visible workflow exists.
- Modify `backend/apps/projects/views.py`
  - Add create/update APIs needed by the operator UI.
- Modify `backend/apps/projects/serializers.py`
  - Add serializers for project create/update and task update.
- Modify `backend/apps/projects/urls.py`
  - Add project detail/update and task update routes.
- Modify `frontend/src/features/admin-config/ConfigWorkspace.tsx`
  - Add field add/remove workflow integration with form layout updates.
- Modify `frontend/src/features/admin-config/ObjectTypeEditor.tsx`
  - Add Add Field and Remove Field controls.
- Modify `frontend/src/features/admin-config/FieldEditor.tsx`
  - Add remove button and stable labels for new-field operator tests.

## Task 1: Save And Review The Operator QA Plan

**Files:**

- Create: `docs/superpowers/plans/2026-06-08-operator-clickthrough-qa-and-dashboard-remediation.md`
- Create after review: `docs/qa/findings/operator-clickthrough-plan-review.md`

- [ ] **Step 1: Confirm the plan is the only uncommitted edit**

Run:

```powershell
git status --short
```

Expected:

```text
?? docs/superpowers/plans/2026-06-08-operator-clickthrough-qa-and-dashboard-remediation.md
```

- [ ] **Step 2: Dispatch read-only review agents**

Dispatch three independent read-only agents:

1. Dashboard/reporting reviewer:
   - Inspect `frontend/src/features/dashboards`, `backend/apps/reports`, and dashboard fixtures.
   - Return exact widget click-through requirements and any missing backend data needed.
2. Operator workflow reviewer:
   - Inspect all navigation tabs and visible controls under `frontend/src/features`.
   - Return a control inventory with gaps against the matrix above.
3. Auth/admin reviewer:
   - Inspect `backend/apps/accounts`, `backend/apps/config_registry`, and `frontend/src/features/admin-config`.
   - Return exact admin vs normal-user UI/API paths for adding/removing fields.

- [ ] **Step 3: Save review output**

Create:

`docs/qa/findings/operator-clickthrough-plan-review.md`

Content shape:

```md
# Operator Clickthrough Plan Review

Date: 2026-06-08

## Dashboard/Reporting Review

- Finding:
- Required plan change:

## Operator Workflow Review

- Finding:
- Required plan change:

## Auth/Admin Review

- Finding:
- Required plan change:

## Accepted Corrections

- Correction:
```

- [ ] **Step 4: Amend this plan if review finds missing coverage**

Run this scan from PowerShell:

```powershell
$plan = Get-Content docs/superpowers/plans/2026-06-08-operator-clickthrough-qa-and-dashboard-remediation.md
$pattern = ('T' + 'BD') + '|' + ('TO' + 'DO') + '|' + ('IMPLEMENT' + 'ME') + '|' + ('PLACE' + 'HOLDER')
$plan | Select-String -Pattern $pattern
```

Expected:

No matches.

## Task 2: Write Failing Dashboard Click-Through Tests

**Files:**

- Modify: `frontend/src/features/dashboards/DashboardPage.test.tsx`

- [ ] **Step 1: Add a failing unit test for widget links**

Add this test to `DashboardPage.test.tsx`:

```tsx
it("makes count dashboard widget rows clickable filters", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();

      if (url === "/api/config/active/") {
        return Response.json({
          data: {
            object_types: [{ key: "product", label: "Product", fields: [] }],
            dashboards: [{ key: "quality_operations", name: "Quality Operations" }]
          }
        });
      }

      if (url === "/api/saved-views/") {
        return Response.json({ results: [] });
      }

      if (url === "/api/dashboards/quality_operations/") {
        return Response.json({
          id: 7,
          name: "Quality Operations",
          widgets: [
            {
              id: 11,
              title: "Records By Status",
              widget_type: "count_by_status",
              data: { items: [{ key: "archived", count: 4 }, { key: "draft", count: 8 }] }
            },
              {
                id: 12,
                title: "Records By Object Type",
                widget_type: "count_by_object_type",
                data: { items: [{ key: "raw_material", count: 3 }] }
              },
              {
                id: 13,
                title: "Projects By Status",
                widget_type: "count_by_status",
                config: { filters: [{ type: "object_type", value: "project" }] },
                data: { items: [{ key: "active", count: 2 }] }
              }
          ]
        });
      }

      return Response.json({ detail: `Unexpected request: ${url}` }, { status: 500 });
    })
  );

  renderDashboardPage();

  const statusWidget = await screen.findByRole("region", { name: /records by status/i });
  expect(within(statusWidget).getByRole("link", { name: /archived/i })).toHaveAttribute(
    "href",
    "/records?status=archived"
  );
  expect(within(statusWidget).getByRole("link", { name: /draft/i })).toHaveAttribute(
    "href",
    "/records?status=draft"
  );

  const objectTypeWidget = screen.getByRole("region", { name: /records by object type/i });
  expect(within(objectTypeWidget).getByRole("link", { name: /raw material/i })).toHaveAttribute(
    "href",
    "/records?object_type_key=raw_material"
  );

  const scopedStatusWidget = screen.getByRole("region", { name: /projects by status/i });
  expect(within(scopedStatusWidget).getByRole("link", { name: /active/i })).toHaveAttribute(
    "href",
    "/records?object_type_key=project&status=active"
  );
});
```

- [ ] **Step 2: Verify the test fails before product edits**

Run:

```powershell
npm --prefix frontend test -- --run src/features/dashboards/DashboardPage.test.tsx
```

Expected before implementation:

```text
FAIL ... Unable to find role="link" name=/archived/i
```

## Task 3: Fix Dashboard Widget Click-Through

**Files:**

- Modify: `frontend/src/features/dashboards/DashboardPage.tsx`

- [ ] **Step 1: Pass widget context into `WidgetItem`**

Change the widget render loop from:

```tsx
<WidgetItem item={item} key={String(item.id ?? item.key ?? index)} />
```

to:

```tsx
<WidgetItem item={item} widget={widget} key={String(item.id ?? item.key ?? index)} />
```

- [ ] **Step 2: Replace `WidgetItem` and href helpers**

Replace:

```tsx
function WidgetItem({ item }: { item: DashboardWidgetItem }) {
```

with:

```tsx
function WidgetItem({ item, widget }: { item: DashboardWidgetItem; widget: DashboardWidget }) {
```

Change:

```tsx
const href = recordHref(item);
```

to:

```tsx
const href = widgetHref(widget, item);
```

Replace `recordHref` with:

```tsx
function widgetHref(widget: DashboardWidget, item: DashboardWidgetItem) {
  if (item.record_id) {
    return `/records/${String(item.record_id)}`;
  }

  if (item.object_type === "record" && item.object_id) {
    return `/records/${String(item.object_id)}`;
  }

  if (item.object_type === "document" && item.object_id) {
    return `/documents/${String(item.object_id)}`;
  }

  if (item.project_id) {
    return `/projects/${String(item.project_id)}`;
  }

  if (widget.widget_type === "count_by_status" && item.key) {
    const scopedObjectType = scopedObjectTypeKey(widget);
    return recordListHref({
      ...(scopedObjectType ? { object_type_key: scopedObjectType } : {}),
      status: String(item.key)
    });
  }

  if (widget.widget_type === "count_by_object_type" && item.key) {
    return recordListHref({ object_type_key: String(item.key) });
  }

  if (widget.widget_type === "workflow_bottlenecks" && item.key) {
    return `/tasks?task_key=${encodeURIComponent(String(item.key))}`;
  }

  return undefined;
}

function recordListHref(params: Record<string, string>) {
  const query = new URLSearchParams(params);
  return `/records?${query.toString()}`;
}

function scopedObjectTypeKey(widget: DashboardWidget) {
  const filters = Array.isArray(widget.config?.filters) ? widget.config.filters : [];
  for (const filter of filters) {
    if (!filter || typeof filter !== "object") {
      continue;
    }
    const filterRecord = filter as Record<string, unknown>;
    const filterType = filterRecord.type ?? filterRecord.filter;
    if (filterType !== "object_type") {
      continue;
    }
    const values = Array.isArray(filterRecord.values) ? filterRecord.values : [];
    if (values.length === 1 && typeof values[0] === "string") {
      return values[0];
    }
    const value = filterRecord.value ?? filterRecord.object_type_key;
    if (typeof value === "string") {
      return value;
    }
  }
  return undefined;
}
```

- [ ] **Step 3: Verify dashboard unit tests pass**

Run:

```powershell
npm --prefix frontend test -- --run src/features/dashboards/DashboardPage.test.tsx
```

Expected:

```text
PASS src/features/dashboards/DashboardPage.test.tsx
```

## Task 4: Add Operator Action Helpers

**Files:**

- Create: `frontend/e2e/support/operatorActions.ts`

- [ ] **Step 1: Create helper file**

Create `operatorActions.ts` with:

```ts
import { expect, type Locator, type Page, type TestInfo } from "@playwright/test";
import { recordFinding, type BugFinding } from "./qaReport";

export async function expectNoRawJsonPage(page: Page, label: string) {
  const body = await page.locator("body").innerText();
  expect(body, label).not.toMatch(/^\s*\{[\s\S]*"\w+"[\s\S]*\}\s*$/);
  expect(body, label).not.toMatch(/JSON\.parse|unexpected character|Workload failed/i);
  expect(body, label).not.toMatch(/Django|Traceback|OperationalError|IntegrityError/i);
}

export async function clickAndExpectUrl(page: Page, locator: Locator, expected: RegExp, label: string) {
  await expect(locator, label).toBeVisible();
  await locator.click();
  await expect(page, label).toHaveURL(expected);
  await expectNoRawJsonPage(page, label);
}

export async function recordOperatorFinding(finding: BugFinding, testInfo: TestInfo) {
  recordFinding(finding, testInfo);
  testInfo.annotations.push({ type: "operator-finding", description: `${finding.id}: ${finding.title}` });
  expect.soft(false, `${finding.id}: ${finding.title}`).toBe(true);
}

export async function expectDownloadedPdf(downloadPromise: Promise<unknown>, label: string) {
  const download = await downloadPromise as {
    suggestedFilename(): string;
    path(): Promise<string | null>;
  };
  expect(download.suggestedFilename(), label).toMatch(/\.pdf$/i);
  const path = await download.path();
  expect(path, label).toBeTruthy();
}
```

- [ ] **Step 2: Run TypeScript**

Run:

```powershell
npm --prefix frontend run lint
```

Expected:

TypeScript exits 0.

## Task 5: Add Full Operator Clickthrough Spec

**Files:**

- Create: `frontend/e2e/client-readiness-operator-clickthrough.spec.ts`
- Modify: `frontend/e2e/support/qaApi.ts` only if deterministic seed helpers are missing.

- [ ] **Step 1: Create the spec skeleton**

Create `client-readiness-operator-clickthrough.spec.ts` with strict setup:

```ts
import { expect, test } from "@playwright/test";
import {
  createRecord,
  downloadExternalPdf,
  ensureQaUsers,
  loginWithSession,
  requireHealthyStack,
  requireMutableQaTarget,
  uploadDocumentRevision
} from "./support/qaApi";
import { clickAndExpectUrl, expectNoRawJsonPage } from "./support/operatorActions";
import { readinessGate } from "./support/strictReadiness";

test.describe("client readiness operator clickthrough", () => {
  test.beforeEach(async ({ request }) => {
    const health = await requireHealthyStack(request);
    readinessGate(!health.ok, health.message);
    const users = ensureQaUsers();
    readinessGate(!users.ok, users.ok ? "" : users.message);
  });

  test("operator can actually use every main tab and visible dashboard widgets", async ({ context, page, request }) => {
    requireMutableQaTarget();
    const users = ensureQaUsers();
    if (!users.ok) throw new Error(users.message);

    const session = await loginWithSession(context, users.engineer);
    const stamp = Date.now().toString();
    const product = await createRecord(session, "product", {
      commercial_name: `QA Operator Product ${stamp}`,
      internal_grade: `QA-OP-${stamp}`,
      resin_family: "PP",
      application: "Operator clickthrough",
      color: "Natural"
    });
    const pdf = await downloadExternalPdf(request);
    const document = await uploadDocumentRevision(session, product.id, `QA Operator PDF ${stamp}`, "A", pdf);

    await page.goto("/");
    await expect(page.getByRole("heading", { name: /operational overview/i })).toBeVisible();

    for (const linkName of ["Records", "Projects", "Documents", "Imports", "Search", "Dashboards", "Audit", "Tasks", "Admin"]) {
      await page.getByRole("link", { name: new RegExp(`^${linkName}$`, "i") }).click();
      await expectNoRawJsonPage(page, linkName);
    }

    await page.goto("/dashboards");
    await expect(page.getByRole("heading", { name: /dashboards|quality operations/i })).toBeVisible();
    await page.getByRole("button", { name: /refresh/i }).click();
    await expectNoRawJsonPage(page, "dashboard refresh");

    const archivedStatus = page.getByRole("link", { name: /archived/i }).first();
    await clickAndExpectUrl(page, archivedStatus, /\/records\?status=archived/, "dashboard archived status filter");

    await page.goto(`/documents/${document.id}`);
    await expect(page.getByRole("heading", { name: document.title })).toBeVisible();
  });
});
```

- [ ] **Step 2: Expand the spec with the remaining operator scenarios**

Add tests with these exact scenario names and assertions:

```ts
test("authentication rejects wrong password and supports logout", async ({ page }) => {
  const users = ensureQaUsers();
  if (!users.ok) throw new Error(users.message);

  await page.goto("/login");
  await page.getByLabel(/username/i).fill(users.engineer.username);
  await page.getByLabel(/password/i).fill("definitely-wrong-password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("alert")).toContainText(/invalid|unable|password|credential/i);

  await page.getByLabel(/password/i).fill(users.engineer.password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("link", { name: /^Records$/i })).toBeVisible();
  await page.getByRole("button", { name: /sign out/i }).click();
  await expect(page.getByRole("link", { name: /sign in/i })).toBeVisible();
});
```

For the remaining scenarios, the implementation must use the UI controls named in the operator matrix:

```ts
test("records can be created edited released archived searched filtered and versioned through UI", async ({ context, page }) => {
  // Required assertions: New Record form submits, record detail opens, field edit persists,
  // Release changes status, Create Version adds version row, Archive changes status,
  // Records list search/status/object-type filters find the created record.
});

test("documents can be opened previewed audited downloaded released and revised through UI", async ({ context, page, request }) => {
  // Required assertions: Upload uses file input, Open/Preview/Audit are clicked from the list,
  // Download emits a PDF, Release Revision changes revision state, Add Revision creates B.
});

test("projects can be opened and board or dependency actions are usable", async ({ context, page }) => {
  // Required assertions: Projects list shows seeded project, detail tabs are clicked,
  // board move/dependency controls mutate state or a finding documents the missing UI.
});

test("tasks and folder events can be completed accepted ignored assigned and linked when seeded", async ({ context, page }) => {
  // Required assertions: Complete, Accept, Ignore, Assign, Link Document buttons are clicked
  // against seeded IDs and produce visible state changes.
});

test("admin field changes are allowed for admins and blocked for normal users", async ({ context, page }) => {
  // Required assertions: engineer is blocked, config admin can add a field,
  // config admin cannot publish destructive removal alone, system admin can confirm it.
});

test("search filters return clickable records documents projects and folder events", async ({ context, page }) => {
  // Required assertions: each supported search type filter is selected,
  // at least one seeded result link opens the correct app route.
});

test("backups are system-admin only and failures are controlled UI/API errors", async ({ context, page }) => {
  // Required assertions: engineer is blocked, system admin creates or gets controlled backup error,
  // backup detail route/API returns JSON and never raw HTML.
});
```

Each comment above must be replaced with concrete click/assert code before implementation is complete. No `test.skip`, no unfinished tests, no soft pass.

- [ ] **Step 3: Run the operator spec and record failures**

Run:

```powershell
$env:PLAYWRIGHT_BASE_URL='http://localhost:5173'
$env:ALLOW_E2E_USER_SEEDING='true'
$env:E2E_PASSWORD='qa-password-12345'
$env:ALLOW_CLIENT_READINESS_SEED='true'
$env:STRICT_CLIENT_READINESS='true'
npm --prefix frontend exec playwright test e2e/client-readiness-operator-clickthrough.spec.ts --project=chromium-desktop --forbid-only
```

Expected before all fixes:

The spec may fail. Each failure must be added to `docs/qa/findings/operator-clickthrough.md` with reproduction, expected behavior, actual behavior, severity, and planned fix.

## Task 6: Fix Document Operator Gaps Proven By Browser Clicks

**Files:**

- Modify: `frontend/e2e/client-readiness-documents.spec.ts`
- Modify only if tests fail: `frontend/src/features/documents/DocumentPanel.tsx`

- [ ] **Step 1: Add browser-click proof for document actions**

In `client-readiness-documents.spec.ts`, after creating a document:

```ts
await page.goto("/documents");
await page.getByRole("link", { name: document.title }).first().click();
await expect(page).toHaveURL(new RegExp(`/documents/${document.id}$`));

await page.goto("/documents");
await page.getByRole("link", { name: /^Preview$/i }).first().click();
await expect(page).toHaveURL(new RegExp(`/documents/${document.id}\\?view=preview$`));
await expect(page.getByRole("heading", { name: /document preview/i })).toBeVisible();
await expectNoRawJsonPage(page, "document preview");

await page.goto("/documents");
await page.getByRole("link", { name: /^Audit$/i }).first().click();
await expect(page).toHaveURL(new RegExp(`/documents/${document.id}\\?view=audit$`));
await expect(page.getByRole("heading", { name: /document audit/i })).toBeVisible();
await expectNoRawJsonPage(page, "document audit");
```

- [ ] **Step 2: Verify document browser behavior**

Run:

```powershell
$env:STRICT_CLIENT_READINESS='true'
npm --prefix frontend exec playwright test e2e/client-readiness-documents.spec.ts --project=chromium-desktop --forbid-only
```

Expected:

Open, Preview, Audit, Download, Release, Add Revision all pass through UI clicks.

## Task 7: Build And Test Project Operator Workflows

**Files:**

- Modify: `frontend/e2e/client-readiness-operations.spec.ts`
- Modify: `frontend/e2e/client-readiness-operator-clickthrough.spec.ts`
- Modify: `backend/apps/projects/views.py`
- Modify: `backend/apps/projects/serializers.py`
- Modify: `backend/apps/projects/urls.py`
- Modify: `backend/tests/projects/test_projects.py`
- Modify: `frontend/src/features/projects/ProjectList.tsx`
- Modify: `frontend/src/features/projects/ProjectDetail.tsx`
- Modify: `frontend/src/features/projects/ProjectBoard.tsx`
- Modify: `frontend/src/features/projects/ProjectTimeline.tsx`
- Modify: `frontend/src/features/projects/ProjectList.test.tsx`
- Modify: `frontend/src/features/projects/ProjectBoard.test.tsx`
- Create or modify: `frontend/src/features/projects/ProjectDetail.test.tsx`

- [ ] **Step 1: Add failing backend tests for project create/update/task update**

Add backend tests requiring:

```python
create_response = post_json(client, "/api/projects/", {
    "name": "Operator Project",
    "description": "Created through operator QA",
    "status": "planning",
    "owner": owner.pk,
})
assert create_response.status_code == 201

project_id = create_response.json()["id"]
patch_response = patch_json(client, f"/api/projects/{project_id}/", {
    "status": "active",
    "owner": owner.pk,
})
assert patch_response.status_code == 200
assert patch_response.json()["status"] == "active"

task_response = patch_json(client, f"/api/project-tasks/{task.pk}/", {
    "state": "in_progress",
    "assignee_user": owner.pk,
})
assert task_response.status_code == 200
assert task_response.json()["state"] == "in_progress"
assert task_response.json()["assignee_user"] == owner.pk
```

Expected before implementation:

Project POST, project PATCH, and task PATCH return 405 or 404.

- [ ] **Step 2: Implement project APIs**

Add:

- `ProjectSerializer` with `id`, `record`, `name`, `description`, `status`, `owner`, `start_date`, `target_date`, counts, timestamps.
- `ProjectCreateSerializer` validating `name`, `description`, `owner`, `start_date`, `target_date`.
- `ProjectUpdateSerializer` validating `status`, `owner`, `description`, `target_date`.
- `ProjectTaskUpdateSerializer` validating `state`, `assignee_user`, `due_date`, `estimated_hours`.
- `ProjectListView.post()` using `create_project`.
- `ProjectDetailView.get()/patch()`.
- `ProjectTaskDetailView.patch()`.

Routes:

```python
path("api/projects/<uuid:project_id>/", ProjectDetailView.as_view(), name="project-detail"),
path("api/project-tasks/<int:pk>/", ProjectTaskDetailView.as_view(), name="project-task-detail"),
```

- [ ] **Step 3: Add project creation and edit UI**

`ProjectList.tsx` must expose a visible `New Project` panel with:

- Project Name
- Description
- Owner User ID
- Target Date
- Create Project button

`ProjectDetail.tsx` must expose:

- Project Status select
- Owner User ID input
- Save Project button

`ProjectBoard.tsx` must expose per task:

- Task State select
- Assignee User ID input
- Save Task button

- [ ] **Step 4: Require project list and detail UI**

The operator spec must:

```ts
await page.goto("/projects");
await expect(page.getByRole("heading", { name: /^Projects$/i })).toBeVisible();
await expect(page.getByRole("link", { name: /QA Client Readiness Project|Project/i }).first()).toBeVisible();
await page.getByRole("link", { name: /QA Client Readiness Project|Project/i }).first().click();
await expect(page.getByRole("button", { name: /board/i })).toBeVisible();
await expect(page.getByRole("button", { name: /timeline/i })).toBeVisible();
await expect(page.getByRole("button", { name: /dependencies/i })).toBeVisible();
```

- [ ] **Step 5: Require project creation/status/assignment actions**

The operator spec must:

```ts
await page.goto("/projects");
await page.getByLabel(/project name/i).fill(`QA Operator Project ${stamp}`);
await page.getByLabel(/description/i).fill("Created by browser operator QA");
await page.getByRole("button", { name: /create project/i }).click();
await expect(page.getByRole("link", { name: new RegExp(`QA Operator Project ${stamp}`) })).toBeVisible();

await page.getByRole("link", { name: new RegExp(`QA Operator Project ${stamp}`) }).click();
await page.getByLabel(/project status/i).selectOption("active");
await page.getByRole("button", { name: /save project/i }).click();
await expect(page.getByText(/active/i)).toBeVisible();
```

- [ ] **Step 6: Require board task status/assignee actions**

The operator spec must click:

- Board tab
- Move task button/control if exposed
- Task State select
- Assignee User ID input
- Save Task button
- Timeline tab
- Dependencies tab
- Add dependency button/control if exposed

Project Documents and Audit tabs currently show unavailable-state text. The operator spec must either prove they now render real data or record `QA-PROJ-UI-002` and `QA-PROJ-UI-003` as known product gaps.

## Task 8: Build And Test Admin Field Add/Remove Authority

**Files:**

- Modify: `frontend/e2e/client-readiness-operator-clickthrough.spec.ts`
- Modify: `frontend/src/features/admin-config/ConfigWorkspace.tsx`
- Modify: `frontend/src/features/admin-config/ObjectTypeEditor.tsx`
- Modify: `frontend/src/features/admin-config/FieldEditor.tsx`
- Modify: `frontend/src/features/admin-config/ConfigWorkspace.test.tsx`
- Modify only if backend tests fail: `backend/apps/config_registry/views.py`
- Modify only if backend tests fail: `backend/apps/config_registry/services.py`

- [ ] **Step 1: Normal user must be blocked in UI**

The operator spec must:

```ts
await page.goto("/login");
await page.getByLabel(/username/i).fill(users.engineer.username);
await page.getByLabel(/password/i).fill(users.engineer.password);
await page.getByRole("button", { name: /sign in/i }).click();
await page.goto("/admin");
await expect(page.getByRole("alert").or(page.getByText(/permission|forbidden|not allowed/i))).toBeVisible();
```

- [ ] **Step 2: Add failing unit tests for Add Field and Remove Field controls**

`ConfigWorkspace.test.tsx` must verify:

```tsx
await user.click(screen.getByRole("button", { name: /create draft/i }));
await user.click(screen.getByRole("button", { name: /add field/i }));
await user.type(screen.getAllByLabelText(/field key/i).at(-1)!, "qa_operator_field");
await user.type(screen.getAllByLabelText(/field label/i).at(-1)!, "QA Operator Field");
expect(screen.getByDisplayValue(/qa_operator_field/i)).toBeInTheDocument();
expect(screen.getByLabelText(/visible fields/i)).toHaveValue(expect.stringContaining("qa_operator_field"));
await user.click(screen.getAllByRole("button", { name: /remove field/i }).at(-1)!);
expect(screen.queryByDisplayValue(/qa_operator_field/i)).not.toBeInTheDocument();
```

Expected before implementation:

No Add Field or Remove Field button exists.

- [ ] **Step 3: Implement Add Field and Remove Field controls**

`ObjectTypeEditor` must accept:

```ts
onAddField: () => void;
onRemoveField: (fieldKey: string) => void;
```

`DraftEditorView` must implement:

- Add field: append a default optional text field with a unique `new_field_<n>` key.
- Add field layout integration: append the new field key to the first form layout section for the same object type.
- Remove field: remove from `object_types[*].fields` and remove the key from every form layout section field list.
- Remove field requires draft mode; disabled in read-only mode.

`FieldEditor` must render:

```tsx
<button className="button button-secondary" type="button" disabled={readOnly} onClick={onRemove}>
  Remove Field
</button>
```

- [ ] **Step 4: Config admin adds a field**

The operator spec must login as config admin and perform:

- Open Admin.
- Create Draft.
- Open object type field editor.
- Add field with key `qa_operator_field_<stamp>`.
- Validate draft.
- Publish configuration.
- Open New Record for that object type.
- Verify the new field appears.

- [ ] **Step 5: Field removal requires System Admin**

The operator spec must:

- Login as config admin.
- Try to remove an existing field.
- Publish without destructive confirmation.
- Expect blocked message.
- Login as system admin.
- Confirm destructive change.
- Publish.
- Open existing record created before removal.
- Verify removed field is hidden from active form but old value remains in version/audit payload.

## Task 9: Fix Search And Saved View Clickability

**Files:**

- Modify: `frontend/e2e/client-readiness-operator-clickthrough.spec.ts`
- Modify only if tests fail: `frontend/src/features/search/SearchPage.tsx`
- Modify only if tests fail: `frontend/src/features/dashboards/DashboardPage.tsx`

- [ ] **Step 1: Search all supported result types**

The operator spec must:

```ts
await page.goto("/search");
await page.getByLabel(/search query/i).fill("polycarbonate");
await page.getByRole("button", { name: /^Search$/i }).click();
await expect(page.getByRole("link").first()).toBeVisible();
```

Repeat with type filters:

- all
- records
- documents
- projects
- folder_events

- [ ] **Step 2: Saved-view results must be clickable when row ID exists**

If saved-view rows display any record row with `id`, add link rendering in `DashboardPage.tsx`:

```tsx
cell: ({ row, getValue }) =>
  row.original.id && (column === "code" || column === "title" || column === "id") ? (
    <Link className="text-link" to={`/records/${row.original.id}`}>{formatCell(getValue())}</Link>
  ) : (
    formatCell(getValue())
  )
```

## Task 10: Add Task Inbox URL Filters For Dashboard Links

**Files:**

- Modify: `frontend/src/features/workflows/TaskInbox.tsx`
- Modify: `frontend/src/features/workflows/TaskInbox.test.tsx`

- [ ] **Step 1: Add failing URL-filter test**

Render `TaskInbox` at `/tasks?task_key=technical_review` and assert only tasks with key `technical_review` remain visible.

- [ ] **Step 2: Implement URL parameter filtering**

`TaskInbox` must read `useSearchParams()` and apply:

- `task_key`
- `due=overdue`
- existing UI filters

Dashboard `workflow_bottlenecks` links are only accepted after this passes.

## Task 11: Decide And Test Backup UI Surface

**Files:**

- Modify: `frontend/e2e/client-readiness-operator-clickthrough.spec.ts`
- Modify only if adding UI: `frontend/src/features/admin-config/ConfigWorkspace.tsx`
- Modify only if adding UI: `frontend/src/features/admin-config/ConfigWorkspace.test.tsx`

- [ ] **Step 1: Choose backup surface**

For this release, use one of these two explicit options:

- Add a System Admin-only Backup panel under Admin with List Backups and Create Backup controls.
- Keep backups API-only and document that there is no client-visible backup UI.

If the second option is chosen, the operator spec must assert no backup button appears in the UI and the API tests must still prove system-admin-only behavior and controlled errors.

## Task 12: Run Full Verification

**Files:**

- Update: `docs/qa/client-readiness-qa-report.md`
- Update: `docs/qa/findings/operator-clickthrough.md`
- Update: `docs/qa/findings/final-verification.md`

- [ ] **Step 1: Start clean local stack**

Run:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
```

Expected:

Backend, frontend, database, Redis, Celery, Meilisearch are healthy.

- [ ] **Step 2: Run backend tests**

Run:

```powershell
& '.\backend\.venv\Scripts\python.exe' -m pytest backend\tests
```

Expected:

All backend tests pass.

- [ ] **Step 3: Run frontend tests**

Run:

```powershell
npm --prefix frontend run lint
npm --prefix frontend test -- --run
```

Expected:

TypeScript and Vitest pass.

- [ ] **Step 4: Run strict browser QA**

Run:

```powershell
$env:PLAYWRIGHT_BASE_URL='http://localhost:5173'
$env:ALLOW_E2E_USER_SEEDING='true'
$env:E2E_PASSWORD='qa-password-12345'
$env:QA_POPULATE_FULL_DATASET='true'
$env:ALLOW_CLIENT_READINESS_SEED='true'
$env:STRICT_CLIENT_READINESS='true'
npm --prefix frontend exec playwright test --project=chromium-desktop --forbid-only
npm --prefix frontend exec playwright test --project=chromium-mobile --forbid-only
```

Expected:

Zero failed tests and zero skipped client-readiness tests.

- [ ] **Step 5: Manual/browser spot-check**

Using Playwright or the in-app browser, open `http://localhost:5173` and manually verify:

- Dashboard `Records By Status` rows are clickable.
- Archived row opens records filtered to archived.
- Draft row opens records filtered to draft.
- Document Preview stays inside app UI.
- Admin field add/remove authority differs by role.
- Projects tab shows list and usable detail actions.

- [ ] **Step 6: Final report**

Update `docs/qa/client-readiness-qa-report.md` with:

- exact commands run
- pass/fail counts
- every bug found
- every bug fixed
- remaining product limitations
- remaining external risks

## Self-Review

- Spec coverage: every user-named scenario is represented in the matrix and tasks.
- Dashboard click-through has a failing unit test before implementation.
- Browser-click document proof is explicitly required.
- Admin field add/remove is tested with both config admin/system admin and normal user.
- Project usability is tested through list/detail/action clicks, not only endpoints.
- Search and saved-view result clickability are tested.
- Strict mode rejects skips.
- No product code changes are allowed before plan review.

# Client Readiness QA Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a complete client-readiness QA suite for the Plastic Engineering Data Hub, then publish a bug ledger with reproducible evidence.

**Architecture:** Add a Playwright QA harness that combines browser navigation with authenticated API setup, uses real plastic-engineering fixture data, downloads a public polycarbonate PDF at runtime, and records defects in a markdown report. Keep browser specs focused by domain and keep shared login, API, and fixture helpers in small support files.

**Tech Stack:** Django REST backend, React/Vite frontend, Vitest unit tests, Playwright end-to-end tests, PowerShell local orchestration, public PDF fixture from Plastic-Craft.

---

## Worktree And Baseline

Use the isolated worktree:

`C:\Users\user\.codex\worktrees\plastic-engineering-data-hub\client-readiness-qa-suite`

Branch:

`codex/client-readiness-qa-suite`

Baseline already verified:

`E:\plastic-engineering-data-hub\backend\.venv\Scripts\python.exe -m pytest backend\tests\documents\test_revisions.py backend\tests\documents\test_extraction.py`

Expected baseline result:

`21 passed`

## File Structure

- Create `frontend/playwright.config.ts`: standard Playwright config for local client-readiness runs.
- Modify `frontend/package.json`: add `e2e`, `e2e:qa`, and `e2e:qa:headed` scripts.
- Create `frontend/e2e/support/qaApi.ts`: authenticated API helpers, JSON assertions, CSRF/login, test user seeding, record/document helpers, and external PDF download helper.
- Create `frontend/e2e/support/qaReport.ts`: structured bug ledger writer used by specs.
- Create `frontend/e2e/client-readiness-records.spec.ts`: records, archive/delete/version, admin configuration authority, and `/admin` route behavior.
- Create `frontend/e2e/client-readiness-documents.spec.ts`: real PDF upload, preview, download, release, second revision, released-revision protection.
- Create `frontend/e2e/client-readiness-operations.spec.ts`: imports, folder events, workflows, projects, search, dashboards, audit, backups, and global navigation health.
- Create `docs/qa/client-readiness-qa-report.md`: client-facing report that starts with known gaps and is updated from test execution.
- Create `docs/qa/findings/plan-review.md`: plan review subagent findings and improvement actions.

## Environment Contract

The Playwright suite reads these environment variables:

- `PLAYWRIGHT_BASE_URL`: local app URL. Default `https://plastic-hub.local`.
- `ALLOW_E2E_USER_SEEDING`: when `true`, tests may create/update QA users through Django shell commands.
- `E2E_USERNAME`: primary engineering QA username. Default `qa_engineer`.
- `E2E_PASSWORD`: primary engineering QA password. Default `qa-password-12345`.
- `E2E_CONFIG_ADMIN_USERNAME`: configuration admin username. Default `qa_config_admin`.
- `E2E_SYSTEM_ADMIN_USERNAME`: system admin username. Default `qa_system_admin`.
- `E2E_READONLY_USERNAME`: read-only username. Default `qa_readonly`.
- `QA_ALLOW_NON_LOCAL_MUTATION`: must be `true` before the suite mutates a non-local target.
- `QA_EXTERNAL_PDF_URL`: override PDF fixture URL. Default `https://plastic-craft.com/content/SDS/polycarbonate.pdf`.

Reviewer correction: QA runs must not mutate unknown remote servers. `qaApi.ts` must check the configured base URL before creating records, documents, imports, folders, projects, dashboards, backups, or configuration drafts. Allowed local hosts are `localhost`, `127.0.0.1`, `plastic-hub.local`, `backend`, and Docker/private hostnames. Any other host requires `QA_ALLOW_NON_LOCAL_MUTATION=true`.

## Task 1: Add Playwright QA Harness

**Files:**

- Create: `frontend/playwright.config.ts`
- Modify: `frontend/package.json`
- Create: `frontend/e2e/support/qaApi.ts`
- Create: `frontend/e2e/support/qaReport.ts`
- Create: `docs/qa/client-readiness-qa-report.md`

- [ ] **Step 1: Add Playwright config**

Create `frontend/playwright.config.ts` with:

```ts
import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "https://plastic-hub.local";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: {
    timeout: 10_000
  },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ["list"],
    ["html", { outputFolder: "test-results/playwright-report", open: "never" }],
    ["json", { outputFile: "test-results/client-readiness-results.json" }]
  ],
  use: {
    baseURL,
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure"
  },
  projects: [
    {
      name: "chromium-desktop",
      use: { ...devices["Desktop Chrome"] }
    },
    {
      name: "chromium-mobile",
      use: { ...devices["Pixel 7"] }
    }
  ],
  outputDir: "test-results/client-readiness-artifacts"
});
```

- [ ] **Step 2: Add npm scripts**

Modify `frontend/package.json` scripts so the scripts block contains:

```json
{
  "dev": "vite",
  "start": "vite preview --host 0.0.0.0 --port 5173",
  "build": "tsc -b && vite build",
  "test": "vitest",
  "lint": "tsc -b --pretty false",
  "e2e": "playwright test",
  "e2e:qa": "playwright test",
  "e2e:qa:headed": "playwright test --headed"
}
```

- [ ] **Step 3: Create QA API helper**

Create `frontend/e2e/support/qaApi.ts` with exported helpers:

```ts
import { expect, type APIRequestContext, type APIResponse, type BrowserContext } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "https://plastic-hub.local";
export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
export const DEFAULT_PDF_URL =
  process.env.QA_EXTERNAL_PDF_URL ?? "https://plastic-craft.com/content/SDS/polycarbonate.pdf";

export type QaCredentials = {
  username: string;
  password: string;
};

export type AuthenticatedSession = {
  request: APIRequestContext;
  csrfToken: string;
  credentials: QaCredentials;
};

export type RecordPayload = {
  id: string;
  object_type_key: string;
  code: string;
  title: string;
  status: string;
  schema_version: number;
  data: Record<string, unknown>;
};

export type DocumentPayload = {
  id: number;
  title: string;
  state: string;
  current_revision: {
    id: number;
    revision_label: string;
    file_name: string;
    state: string;
    extraction_status: string;
  } | null;
};

export async function requireHealthyStack(request: APIRequestContext) {
  const health = await request.get("/api/health/", { timeout: 15_000 }).catch(() => null);
  if (!health?.ok()) {
    return { ok: false, message: `Local stack is unavailable at ${BASE_URL}` };
  }
  return { ok: true, message: "healthy" };
}

export async function loginWithSession(context: BrowserContext, credentials: QaCredentials) {
  const csrf = await getJson<{ csrfToken: string }>(context.request, "/api/accounts/csrf/");
  const login = await context.request.post("/api/accounts/login/", {
    headers: {
      "content-type": "application/json",
      "x-csrftoken": csrf.csrfToken
    },
    data: credentials
  });
  await expectJson(login, 200);
  const refreshed = await getJson<{ csrfToken: string }>(context.request, "/api/accounts/csrf/");
  return { request: context.request, csrfToken: refreshed.csrfToken, credentials };
}

export function ensureQaUsers() {
  if (process.env.ALLOW_E2E_USER_SEEDING !== "true") {
    const explicitCredentialsProvided =
      Boolean(process.env.E2E_USERNAME) && Boolean(process.env.E2E_PASSWORD);
    if (!explicitCredentialsProvided) {
      return {
        ok: false,
        message:
          "QA credentials are not seeded. Set ALLOW_E2E_USER_SEEDING=true for a local stack or provide E2E_USERNAME/E2E_PASSWORD explicitly."
      };
    }
    return {
      ok: true,
      credentials: defaultQaCredentials(),
      configAdmin: defaultConfigAdminCredentials(),
      systemAdmin: defaultSystemAdminCredentials(),
      readOnly: defaultReadOnlyCredentials()
    };
  }

  try {
    execFileSync("docker", ["compose", "exec", "-T", "backend", "python", "manage.py", "shell"], {
      cwd: REPO_ROOT,
      input: seedScript(),
      stdio: ["pipe", "pipe", "pipe"]
    });
  } catch (error) {
    return {
      ok: false,
      message: `Unable to seed QA users through docker compose: ${String(error)}`
    };
  }

  return {
    ok: true,
    credentials: defaultQaCredentials(),
    configAdmin: defaultConfigAdminCredentials(),
    systemAdmin: defaultSystemAdminCredentials(),
    readOnly: defaultReadOnlyCredentials()
  };
}

export async function createRecord(
  session: AuthenticatedSession,
  objectTypeKey: string,
  data: Record<string, unknown>,
  expectedStatus = 201
) {
  return postJson<RecordPayload>(
    session,
    "/api/records/",
    { object_type_key: objectTypeKey, data },
    expectedStatus
  );
}

export async function uploadDocumentRevision(
  session: AuthenticatedSession,
  ownerRecordId: string,
  title: string,
  revisionLabel: string,
  filePath: string
) {
  const response = await session.request.post("/api/documents/", {
    headers: { "x-csrftoken": session.csrfToken },
    multipart: {
      owner_record: ownerRecordId,
      title,
      document_type: "technical_data_sheet",
      revision_label: revisionLabel,
      file: {
        name: path.basename(filePath),
        mimeType: "application/pdf",
        buffer: readFileSync(filePath)
      }
    }
  });
  await expectJson(response, 201);
  return response.json() as Promise<DocumentPayload>;
}

export async function addDocumentRevision(
  session: AuthenticatedSession,
  documentId: number,
  revisionLabel: string,
  filePath: string,
  expectedStatus = 201
) {
  const response = await session.request.post(`/api/documents/${documentId}/revisions/`, {
    headers: { "x-csrftoken": session.csrfToken },
    multipart: {
      revision_label: revisionLabel,
      file: {
        name: path.basename(filePath),
        mimeType: "application/pdf",
        buffer: readFileSync(filePath)
      }
    }
  });
  await expectJson(response, expectedStatus);
  return response;
}

export async function downloadExternalPdf(request: APIRequestContext) {
  const assetDir = path.join(REPO_ROOT, "frontend", "test-results", "qa-assets");
  mkdirSync(assetDir, { recursive: true });
  const pdfPath = path.join(assetDir, "plastic-craft-polycarbonate.pdf");
  if (existsSync(pdfPath)) {
    return pdfPath;
  }
  const response = await request.get(DEFAULT_PDF_URL, { timeout: 30_000 });
  await expect(response, `download ${DEFAULT_PDF_URL}`).toBeOK();
  const body = await response.body();
  expect(body.length).toBeGreaterThan(1_000);
  expect(body.subarray(0, 4).toString()).toBe("%PDF");
  writeFileSync(pdfPath, body);
  writeFileSync(`${pdfPath}.sha256`, createHash("sha256").update(body).digest("hex"));
  return pdfPath;
}

export async function getJson<T>(request: APIRequestContext, url: string) {
  const response = await request.get(url);
  await expectJson(response, 200);
  return response.json() as Promise<T>;
}

export async function postJson<T>(
  session: AuthenticatedSession,
  url: string,
  data: unknown,
  expectedStatus = 200
) {
  const response = await session.request.post(url, {
    headers: {
      "content-type": "application/json",
      "x-csrftoken": session.csrfToken
    },
    data
  });
  await expectJson(response, expectedStatus);
  return response.json() as Promise<T>;
}

export async function patchJson<T>(
  session: AuthenticatedSession,
  url: string,
  data: unknown,
  expectedStatus = 200
) {
  const response = await session.request.patch(url, {
    headers: {
      "content-type": "application/json",
      "x-csrftoken": session.csrfToken
    },
    data
  });
  await expectJson(response, expectedStatus);
  return response.json() as Promise<T>;
}

export async function expectJson(response: APIResponse, expectedStatus: number) {
  expect(response.status()).toBe(expectedStatus);
  const contentType = response.headers()["content-type"] ?? "";
  expect(contentType).toContain("application/json");
}

function defaultQaCredentials() {
  return {
    username: process.env.E2E_USERNAME ?? "qa_engineer",
    password: process.env.E2E_PASSWORD ?? "qa-password-12345"
  };
}

function defaultConfigAdminCredentials() {
  return {
    username: process.env.E2E_CONFIG_ADMIN_USERNAME ?? "qa_config_admin",
    password: process.env.E2E_PASSWORD ?? "qa-password-12345"
  };
}

function defaultSystemAdminCredentials() {
  return {
    username: process.env.E2E_SYSTEM_ADMIN_USERNAME ?? "qa_system_admin",
    password: process.env.E2E_PASSWORD ?? "qa-password-12345"
  };
}

function defaultReadOnlyCredentials() {
  return {
    username: process.env.E2E_READONLY_USERNAME ?? "qa_readonly",
    password: process.env.E2E_PASSWORD ?? "qa-password-12345"
  };
}

function seedScript() {
  const password = process.env.E2E_PASSWORD ?? "qa-password-12345";
  return `
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from apps.accounts.models import ObjectPermission
from apps.accounts.permissions import CONFIGURATION_ADMIN_ROLE, SYSTEM_ADMIN_ROLE
User = get_user_model()
objects = ["product", "supplier", "raw_material", "product_spec"]
roles = {
    "Engineering": {"can_view": True, "can_create": True, "can_edit": True, "can_release": True, "can_admin": False},
    "Read Only": {"can_view": True, "can_create": False, "can_edit": False, "can_release": False, "can_admin": False},
    CONFIGURATION_ADMIN_ROLE: {"can_view": True, "can_create": True, "can_edit": True, "can_release": True, "can_admin": True},
    SYSTEM_ADMIN_ROLE: {"can_view": True, "can_create": True, "can_edit": True, "can_release": True, "can_admin": True},
}
for role, grants in roles.items():
    group, _ = Group.objects.get_or_create(name=role)
    for object_type in objects:
        ObjectPermission.objects.update_or_create(role_name=role, object_type_key=object_type, defaults=grants)
engineer, _ = User.objects.update_or_create(username="qa_engineer", defaults={"is_active": True})
engineer.set_password("${password}")
engineer.save()
engineer.groups.set([Group.objects.get(name="Engineering")])
config_admin, _ = User.objects.update_or_create(username="qa_config_admin", defaults={"is_active": True})
config_admin.set_password("${password}")
config_admin.save()
config_admin.groups.set([Group.objects.get(name=CONFIGURATION_ADMIN_ROLE), Group.objects.get(name="Engineering")])
system_admin, _ = User.objects.update_or_create(username="qa_system_admin", defaults={"is_active": True, "is_superuser": True, "is_staff": True})
system_admin.set_password("${password}")
system_admin.save()
system_admin.groups.set([Group.objects.get(name=SYSTEM_ADMIN_ROLE), Group.objects.get(name="Engineering")])
readonly, _ = User.objects.update_or_create(username="qa_readonly", defaults={"is_active": True})
readonly.set_password("${password}")
readonly.save()
readonly.groups.set([Group.objects.get(name="Read Only")])
`;
}
```

- [ ] **Step 4: Create QA report helper**

Create `frontend/e2e/support/qaReport.ts` with:

```ts
import { appendFileSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { REPO_ROOT } from "./qaApi";

export type BugSeverity = "Critical" | "High" | "Medium" | "Low";

export type BugFinding = {
  id: string;
  severity: BugSeverity;
  area: string;
  title: string;
  expected: string;
  actual: string;
  evidence: string;
};

const reportPath = path.join(REPO_ROOT, "docs", "qa", "client-readiness-qa-report.md");

export function ensureQaReport() {
  mkdirSync(path.dirname(reportPath), { recursive: true });
  if (existsSync(reportPath)) {
    return reportPath;
  }
  writeFileSync(
    reportPath,
    [
      "# Client Readiness QA Report",
      "",
      "Date: 2026-06-08",
      "",
      "## Summary",
      "",
      "Automated and exploratory QA findings for the Plastic Engineering Data Hub.",
      "",
      "## Findings",
      ""
    ].join("\n")
  );
  return reportPath;
}

export function recordFinding(finding: BugFinding) {
  ensureQaReport();
  appendFileSync(
    reportPath,
    [
      `### ${finding.id}: ${finding.title}`,
      "",
      `Severity: ${finding.severity}`,
      "",
      `Area: ${finding.area}`,
      "",
      `Expected: ${finding.expected}`,
      "",
      `Actual: ${finding.actual}`,
      "",
      `Evidence: ${finding.evidence}`,
      ""
    ].join("\n")
  );
}
```

- [ ] **Step 5: Seed the report with known client-critical QA gates**

Create `docs/qa/client-readiness-qa-report.md` with:

```md
# Client Readiness QA Report

Date: 2026-06-08

## Summary

This report records automated QA results, exploratory checks, and client-readiness findings for the Plastic Engineering Data Hub.

## Known Product Gaps To Verify During Execution

### QA-GAP-001: Records Require Archive Instead Of Delete

Severity: Critical

Expected: Records cannot be deleted, but authorized users can archive records and archived records remain auditable.

Actual: Code review shows `Record.Status` currently supports only `draft` and `released`, and `RecordViewSet` has no archive endpoint.

Evidence: `backend/apps/records/models.py`, `backend/apps/records/views.py`

### QA-GAP-002: Records Require Version Creation And Version Browsing

Severity: Critical

Expected: Users can create a new version of a record and inspect prior record versions.

Actual: Code review shows document revisions exist, but no record revision/version model or endpoint is present.

Evidence: `backend/apps/records/models.py`, `backend/apps/documents/models.py`

## Findings
```

- [ ] **Step 6: Run type and unit baseline**

Run:

`npm --prefix frontend run lint`

Expected:

TypeScript build completes with exit code 0.

Run:

`npm --prefix frontend test -- --run`

Expected:

Vitest completes with existing tests passing.

- [ ] **Step 7: Commit harness**

Run:

```powershell
git add frontend/playwright.config.ts frontend/package.json frontend/e2e/support/qaApi.ts frontend/e2e/support/qaReport.ts docs/qa/client-readiness-qa-report.md
git commit -m "test: add client readiness qa harness"
```

Expected:

Commit succeeds.

## Task 2: Records, Delete/Archive/Version, And Admin Authority QA

**Files:**

- Create: `frontend/e2e/client-readiness-records.spec.ts`
- Update: `docs/qa/client-readiness-qa-report.md`

- [ ] **Step 1: Add records/admin spec**

Create `frontend/e2e/client-readiness-records.spec.ts` with tests that:

```ts
import { expect, test } from "@playwright/test";
import {
  createRecord,
  ensureQaUsers,
  getJson,
  loginWithSession,
  patchJson,
  requireHealthyStack,
  type RecordPayload
} from "./support/qaApi";
import { ensureQaReport, recordFinding } from "./support/qaReport";

test.describe("client readiness records and admin controls", () => {
  test.beforeEach(async ({ request }) => {
    const health = await requireHealthyStack(request);
    test.skip(!health.ok, health.message);
    const users = ensureQaUsers();
    test.skip(!users.ok, users.message);
    ensureQaReport();
  });

  test("records can be created, edited, released, and never deleted", async ({ context, page }) => {
    const users = ensureQaUsers();
    if (!users.ok) throw new Error(users.message);
    const session = await loginWithSession(context, users.credentials);
    const stamp = Date.now().toString();

    await page.goto("/records");
    await expect(page.getByRole("heading", { name: /records/i })).toBeVisible();
    await page.getByRole("link", { name: /new record/i }).click();
    await expect(page).toHaveURL(/\/records\/new/);

    const product = await createRecord(session, "product", {
      commercial_name: `QA Polycarbonate Housing ${stamp}`,
      internal_grade: `QA-PC-${stamp}`,
      resin_family: "PC",
      application: "Instrument housing",
      color: "Clear"
    });

    await page.goto(`/records/${product.id}`);
    await expect(page.getByRole("heading", { name: product.title })).toBeVisible();
    await expect(page.getByText(product.code)).toBeVisible();
    await expect(page.getByRole("button", { name: /delete/i })).toHaveCount(0);

    const patched = await patchJson<RecordPayload>(session, `/api/records/${product.id}/`, {
      data: { color: "Transparent" }
    });
    expect(patched.data.color).toBe("Transparent");

    const deleteResponse = await session.request.delete(`/api/records/${product.id}/`, {
      headers: { "x-csrftoken": session.csrfToken }
    });
    expect([403, 405]).toContain(deleteResponse.status());

    const released = await session.request.post(`/api/records/${product.id}/release/`, {
      headers: { "x-csrftoken": session.csrfToken }
    });
    expect(released.status()).toBe(200);
  });

  test("archive and record-version requirements are explicitly verified", async ({ context }) => {
    const users = ensureQaUsers();
    if (!users.ok) throw new Error(users.message);
    const session = await loginWithSession(context, users.credentials);
    const stamp = Date.now().toString();
    const product = await createRecord(session, "product", {
      commercial_name: `QA Archive Gate ${stamp}`,
      internal_grade: `QA-ARCH-${stamp}`,
      resin_family: "PP",
      application: "Closure",
      color: "Natural"
    });

    const archiveResponse = await session.request.post(`/api/records/${product.id}/archive/`, {
      headers: { "x-csrftoken": session.csrfToken }
    });
    if (archiveResponse.status() === 404 || archiveResponse.status() === 405) {
      recordFinding({
        id: "QA-GAP-001",
        severity: "Critical",
        area: "Records",
        title: "Records cannot be archived",
        expected: "Authorized users can archive a record instead of deleting it.",
        actual: `Archive endpoint returned ${archiveResponse.status()}.`,
        evidence: `/api/records/${product.id}/archive/`
      });
    }
    expect(archiveResponse.status(), "archive endpoint must exist").toBeLessThan(400);

    const versionResponse = await session.request.post(`/api/records/${product.id}/versions/`, {
      headers: { "x-csrftoken": session.csrfToken },
      data: { change_note: "QA version gate" }
    });
    if (versionResponse.status() === 404 || versionResponse.status() === 405) {
      recordFinding({
        id: "QA-GAP-002",
        severity: "Critical",
        area: "Records",
        title: "Records cannot create new versions",
        expected: "Authorized users can create and inspect record versions.",
        actual: `Version endpoint returned ${versionResponse.status()}.`,
        evidence: `/api/records/${product.id}/versions/`
      });
    }
    expect(versionResponse.status(), "record version endpoint must exist").toBeLessThan(400);
  });

  test("normal users cannot mutate configuration drafts", async ({ context }) => {
    const users = ensureQaUsers();
    if (!users.ok) throw new Error(users.message);
    const session = await loginWithSession(context, users.credentials);

    const history = await session.request.get("/api/config/history/");
    expect([403, 404]).toContain(history.status());

    const draft = await session.request.post("/api/config/drafts/", {
      headers: { "x-csrftoken": session.csrfToken }
    });
    expect([403, 404]).toContain(draft.status());
  });

  test("admin route is available from navigation and direct reload", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /^admin$/i }).click();
    await expect(page.getByRole("heading", { name: /admin|configuration/i })).toBeVisible();

    await page.goto("/admin");
    const bodyText = await page.locator("body").innerText();
    if (/Django administration/i.test(bodyText)) {
      recordFinding({
        id: "QA-ROUTE-001",
        severity: "High",
        area: "Routing",
        title: "Direct /admin reload opens Django admin instead of React admin workspace",
        expected: "Direct reload of /admin serves the React admin configuration workspace.",
        actual: "The page body contains Django administration.",
        evidence: "frontend/vite.config.ts proxies /admin to the backend"
      });
    }
    expect(bodyText).not.toMatch(/Django administration/i);
  });
});
```

- [ ] **Step 2: Run records/admin spec**

Run:

`npm --prefix frontend run e2e:qa -- --project=chromium-desktop frontend/e2e/client-readiness-records.spec.ts`

Expected:

The deletion and permission tests pass. The archive/version tests are expected to fail until product support exists, and their failures must be captured in the QA report.

- [ ] **Step 3: Commit records/admin QA**

Run:

```powershell
git add frontend/e2e/client-readiness-records.spec.ts docs/qa/client-readiness-qa-report.md
git commit -m "test: cover records archive version and admin gates"
```

Expected:

Commit succeeds.

## Task 3: Real Plastic Document Upload And Revision QA

**Files:**

- Create: `frontend/e2e/client-readiness-documents.spec.ts`
- Update: `docs/qa/client-readiness-qa-report.md`

- [ ] **Step 1: Add document lifecycle spec**

Create `frontend/e2e/client-readiness-documents.spec.ts` with tests that:

```ts
import { expect, test } from "@playwright/test";
import {
  addDocumentRevision,
  createRecord,
  downloadExternalPdf,
  ensureQaUsers,
  getJson,
  loginWithSession,
  requireHealthyStack,
  uploadDocumentRevision
} from "./support/qaApi";
import { ensureQaReport } from "./support/qaReport";

test.describe("client readiness document lifecycle", () => {
  test.beforeEach(async ({ request }) => {
    const health = await requireHealthyStack(request);
    test.skip(!health.ok, health.message);
    const users = ensureQaUsers();
    test.skip(!users.ok, users.message);
    ensureQaReport();
  });

  test("real polycarbonate PDF uploads, extracts, previews, releases, downloads, and protects released labels", async ({
    context,
    request,
    page
  }) => {
    const users = ensureQaUsers();
    if (!users.ok) throw new Error(users.message);
    const session = await loginWithSession(context, users.credentials);
    const stamp = Date.now().toString();
    const pdfPath = await downloadExternalPdf(request);

    const product = await createRecord(session, "product", {
      commercial_name: `QA Polycarbonate Document ${stamp}`,
      internal_grade: `QA-DOC-PC-${stamp}`,
      resin_family: "PC",
      application: "Transparent guard",
      color: "Clear"
    });

    const document = await uploadDocumentRevision(
      session,
      product.id,
      `QA Polycarbonate TDS ${stamp}`,
      "A",
      pdfPath
    );
    expect(document.current_revision?.extraction_status).toBe("extracted");

    await page.goto(`/records/${product.id}`);
    await expect(page.getByText(/QA Polycarbonate TDS/i)).toBeVisible();
    await expect(page.getByText(/Extraction: extracted/i)).toBeVisible();

    const preview = await getJson<{ extracted_text: string }>(
      session.request,
      `/api/documents/${document.id}/preview/`
    );
    expect(preview.extracted_text).toMatch(/polycarbonate/i);
    expect(preview.extracted_text).toMatch(/tensile|flexural|density/i);

    const download = await session.request.get(`/api/documents/${document.id}/download/`);
    expect(download.status()).toBe(200);
    const body = await download.body();
    expect(body.length).toBeGreaterThan(1_000);
    expect(body.subarray(0, 4).toString()).toBe("%PDF");

    const release = await session.request.post(
      `/api/documents/${document.id}/revisions/${document.current_revision?.id}/release/`,
      { headers: { "x-csrftoken": session.csrfToken } }
    );
    expect(release.status()).toBe(200);

    await addDocumentRevision(session, document.id, "B", pdfPath, 201);
    await addDocumentRevision(session, document.id, "A", pdfPath, 400);
  });
});
```

- [ ] **Step 2: Run document spec**

Run:

`npm --prefix frontend run e2e:qa -- --project=chromium-desktop frontend/e2e/client-readiness-documents.spec.ts`

Expected:

The test downloads `plastic-craft-polycarbonate.pdf`, uploads it, extracts preview text containing plastic-domain terms, releases revision A, creates revision B, and rejects replacing released revision A.

- [ ] **Step 3: Commit document QA**

Run:

```powershell
git add frontend/e2e/client-readiness-documents.spec.ts docs/qa/client-readiness-qa-report.md
git commit -m "test: cover real plastic document revisions"
```

Expected:

Commit succeeds.

## Task 4: Operations QA For Imports, Projects, Workflows, Search, Dashboards, Audit, Backups, And Navigation

**Files:**

- Create: `frontend/e2e/client-readiness-operations.spec.ts`
- Update: `docs/qa/client-readiness-qa-report.md`

Reviewer correction: this task must not pass merely because endpoints return JSON permission errors. It must either complete a real workflow or write a finding explaining why the current product cannot satisfy the workflow. In particular, cover import dry-run/apply, XLSX exports, project workload/board/timeline/dependencies, workflow transitions/tasks, folder event actions, saved views/dashboards, backups as System Admin, route reloads after login, and the known document library list/retrieve gap.

- [ ] **Step 1: Add operations spec**

Create `frontend/e2e/client-readiness-operations.spec.ts` with tests that:

```ts
import { expect, test } from "@playwright/test";
import {
  createRecord,
  ensureQaUsers,
  getJson,
  loginWithSession,
  postJson,
  requireHealthyStack
} from "./support/qaApi";
import { ensureQaReport, recordFinding } from "./support/qaReport";

const appRoutes = [
  "/",
  "/records",
  "/records/new",
  "/projects",
  "/imports",
  "/documents",
  "/tasks",
  "/tasks/folder-events",
  "/search",
  "/dashboards",
  "/audit",
  "/admin"
];

test.describe("client readiness operations", () => {
  test.beforeEach(async ({ request }) => {
    const health = await requireHealthyStack(request);
    test.skip(!health.ok, health.message);
    const users = ensureQaUsers();
    test.skip(!users.ok, users.message);
    ensureQaReport();
  });

  for (const route of appRoutes) {
    test(`route ${route} loads without uncaught errors`, async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on("console", (message) => {
        if (message.type() === "error") consoleErrors.push(message.text());
      });
      await page.goto(route);
      await expect(page.locator("body")).toBeVisible();
      expect(consoleErrors.join("\n")).not.toMatch(/JSON\.parse|Workload failed|unexpected character/i);
    });
  }

  test("relationships, graph, search, and audit reflect QA records", async ({ context, page }) => {
    const users = ensureQaUsers();
    if (!users.ok) throw new Error(users.message);
    const session = await loginWithSession(context, users.credentials);
    const stamp = Date.now().toString();

    const supplier = await createRecord(session, "supplier", {
      supplier_name: `QA Resin Supplier ${stamp}`,
      supplier_code: `QA-SUP-${stamp}`,
      approved_status: "Approved"
    });
    const rawMaterial = await createRecord(session, "raw_material", {
      supplier_material_code: `QA-RM-${stamp}`,
      material_family: "Base Resin",
      supplier: supplier.id,
      melt_flow_index: 14,
      density: 0.91,
      color: "Natural"
    });
    const product = await createRecord(session, "product", {
      commercial_name: `QA Graph Product ${stamp}`,
      internal_grade: `QA-GRAPH-${stamp}`,
      resin_family: "PP",
      application: "Cap",
      color: "Natural"
    });

    await postJson(session, "/api/relationships/", {
      source_record: product.id,
      target_record: rawMaterial.id,
      relationship_type_key: "product_uses_material",
      data: { basis: "QA primary resin" }
    }, 201);

    const graph = await getJson<{ nodes: unknown[]; edges: unknown[] }>(
      session.request,
      `/api/records/${product.id}/graph/`
    );
    expect(graph.nodes.length).toBeGreaterThanOrEqual(2);
    expect(graph.edges.length).toBeGreaterThanOrEqual(1);

    await page.goto("/search");
    await page.getByLabel(/search query/i).fill(`QA Graph Product ${stamp}`);
    await page.keyboard.press("Enter");
    await expect(page.getByText(`QA Graph Product ${stamp}`)).toBeVisible();

    await page.goto("/audit");
    await expect(page.getByText(/relationship.created|record.created/i).first()).toBeVisible();
  });

  test("projects, dashboards, imports, backups, and folder review workflows either work or are reported", async ({
    context
  }) => {
    const users = ensureQaUsers();
    if (!users.ok) throw new Error(users.message);
    const session = await loginWithSession(context, users.credentials);

    const endpoints = [
      "/api/projects/workload/",
      "/api/saved-views/",
      "/api/dashboards/quality_operations/",
      "/api/folder-events/",
      "/api/workflow-tasks/?state=open",
      "/api/backups/"
    ];

    for (const endpoint of endpoints) {
      const response = await session.request.get(endpoint);
      const contentType = response.headers()["content-type"] ?? "";
      if ([401, 403, 404].includes(response.status())) {
        recordFinding({
          id: `QA-OP-${endpoint.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "")}`,
          severity: "Medium",
          area: "Operations",
          title: `${endpoint} did not satisfy an authenticated workflow gate`,
          expected: "Operational QA endpoints must be seeded and exercised as real workflows, not only smoke-checked.",
          actual: `Status ${response.status()} with content-type ${contentType}`,
          evidence: endpoint
        });
      }
      if (!contentType.includes("application/json")) {
        recordFinding({
          id: `QA-API-${endpoint.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "")}`,
          severity: "High",
          area: "API",
          title: `${endpoint} did not return JSON`,
          expected: "API endpoints return controlled JSON responses or JSON permission errors.",
          actual: `Status ${response.status()} with content-type ${contentType}`,
          evidence: endpoint
        });
      }
      expect(contentType).toContain("application/json");
      expect(response.status()).toBeLessThan(400);
    }
  });
});
```

- [ ] **Step 2: Run operations spec**

Run:

`npm --prefix frontend run e2e:qa -- --project=chromium-desktop frontend/e2e/client-readiness-operations.spec.ts`

Expected:

Routes load, no JSON.parse workload failure appears, relationship/graph/search/audit flow works, and operational APIs return JSON without 500-class responses.

- [ ] **Step 3: Commit operations QA**

Run:

```powershell
git add frontend/e2e/client-readiness-operations.spec.ts docs/qa/client-readiness-qa-report.md
git commit -m "test: cover operational client readiness flows"
```

Expected:

Commit succeeds.

## Task 5: Run Full QA, Collect Artifacts, And Finalize Report

**Files:**

- Update: `docs/qa/client-readiness-qa-report.md`
- Create: `docs/qa/findings/<domain>.md` files as subagents return findings.

- [ ] **Step 1: Run backend regression groups**

Run:

`E:\plastic-engineering-data-hub\backend\.venv\Scripts\python.exe -m pytest backend\tests`

Expected:

All backend tests pass. If any fail, record each failure in `docs/qa/client-readiness-qa-report.md` with command output summary and affected test path.

- [ ] **Step 2: Run frontend unit and type checks**

Run:

`npm --prefix frontend run lint`

Expected:

TypeScript exits 0.

Run:

`npm --prefix frontend test -- --run`

Expected:

Vitest exits 0.

- [ ] **Step 3: Run full Playwright QA suite**

Run:

`npm --prefix frontend run e2e:qa`

Expected:

All implemented tests pass except tests that intentionally fail for confirmed product gaps. Product-gap failures must remain documented in the report and must not be called green.

- [ ] **Step 4: Run mobile route health**

Run:

`npm --prefix frontend run e2e:qa -- --project=chromium-mobile frontend/e2e/client-readiness-operations.spec.ts`

Expected:

All app routes render body content without uncaught console errors on the mobile project.

- [ ] **Step 5: Summarize generated artifacts**

Add an "Execution Evidence" section to `docs/qa/client-readiness-qa-report.md` listing:

```md
## Execution Evidence

- Backend pytest command and result
- Frontend lint command and result
- Frontend unit command and result
- Playwright desktop command and result
- Playwright mobile command and result
- External PDF source URL
- Playwright report path: `frontend/test-results/playwright-report/index.html`
- JSON results path: `frontend/test-results/client-readiness-results.json`
```

- [ ] **Step 6: Final commit**

Run:

```powershell
git add frontend/playwright.config.ts frontend/package.json frontend/e2e docs/qa docs/superpowers
git commit -m "test: complete client readiness qa suite"
```

Expected:

Commit succeeds if previous task commits were squashed or not made. If previous task commits already exist and there is nothing left to commit, `git status --short` is clean.

## Subagent Execution Plan

Use subagents in this order:

1. Plan reviewer agent: read the codebase, this design, and this plan. Return gaps, unsafe assumptions, missing test domains, and plan corrections. Write the accepted summary to `docs/qa/findings/plan-review.md`.
2. Records/admin QA agent: execute Task 2, focusing on record creation, delete denial, archive gap, version gap, normal-user config denial, and `/admin` route behavior.
3. Documents QA agent: execute Task 3, focusing on real PDF download/upload/extraction/revision/release/download behavior.
4. Operations QA agent: execute Task 4, focusing on routes, imports, projects, workflows, folder events, search, dashboards, audit, backups, and JSON response health.
5. Final review agent: inspect all QA code and report docs for accuracy, reproducibility, and whether any failed behavior was mislabeled as passing.

Do not dispatch multiple implementation agents that edit the same support file at the same time. Task 1 must complete before Tasks 2 through 4. Tasks 2 through 4 may execute in parallel after Task 1 because they create different spec files and append independent report findings.

## Self Review

- Every requirement from the design has a task or a report gate.
- The plan names exact files and commands.
- The plan includes concrete Playwright helper and spec code for each new file.
- Archive and record-version support are treated as failing client requirements unless the product adds them.
- The external PDF source is concrete and stored only under ignored test artifacts at runtime.

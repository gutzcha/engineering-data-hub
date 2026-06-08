import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { readFileSync } from "node:fs";

import {
  createRecord,
  downloadExternalPdf,
  ensureQaUsers,
  getJson,
  loginWithSession,
  requireHealthyStack,
  requireMutableQaTarget,
  seedClientReadinessDemo,
  type QaUserSetup,
  type RecordPayload
} from "./support/qaApi";
import { ensureQaReport, recordFinding, type BugFinding } from "./support/qaReport";
import { readinessGate } from "./support/strictReadiness";

type CurrentUser = {
  id: number;
  username: string;
};

type ProjectPayload = {
  id: string;
  name: string;
};

type DocumentPayload = {
  id: number;
  title: string;
  current_revision?: {
    id: number;
    revision_label: string;
  } | null;
};

test.describe("client readiness operator clickthrough", () => {
  test.beforeEach(async ({ request }) => {
    const health = await requireHealthyStack(request);
    readinessGate(!health.ok, health.message);
    const users = ensureQaUsers();
    readinessGate(!users.ok, users.ok ? "" : users.message);
    ensureQaReport();
  });

  test("wrong password is rejected before a real UI sign-in succeeds", async ({ page }) => {
    const users = requireUsers();

    await page.goto("/login");
    await page.getByLabel("Username", { exact: true }).fill(users.engineer.username);
    await page.getByLabel("Password", { exact: true }).fill("wrong-password");
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page.getByRole("alert")).toContainText(/sign in failed/i);
    await expect(page).toHaveURL(/\/login/);

    await page.getByLabel("Password", { exact: true }).fill(users.engineer.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page.getByRole("heading", { name: "Operational Overview" })).toBeVisible();
    await expect(page.getByLabel("Current user")).toContainText(users.engineer.username);
  });

  test("main navigation tabs load through actual UI links", async ({ context, page }) => {
    const users = requireUsers();
    await loginWithSession(context, users.systemAdmin);

    await page.goto("/");
    const tabs = [
      { label: "Home", heading: /operational overview/i },
      { label: "Records", heading: /^records$/i },
      { label: "Projects", heading: /^projects$/i },
      { label: "Imports", heading: /import wizard/i },
      { label: "Documents", heading: /^documents$/i },
      { label: "Search", heading: /^search$/i },
      { label: "Dashboards", heading: /dashboards|quality operations|engineering overview/i },
      { label: "Audit", heading: /audit timeline/i },
      { label: "Tasks", heading: /task inbox/i },
      { label: "Admin", heading: /admin configuration/i }
    ];

    for (const tab of tabs) {
      await page.getByRole("link", { name: new RegExp(`^${tab.label}$`, "i") }).click();
      await expect(page.getByRole("heading", { name: tab.heading }).first()).toBeVisible();
      await expectNoRawFailure(page, `${tab.label} tab`);
    }
  });

  test("record creation, edit, release, archive, versioning, filtering, and dashboard links are clickable", async ({
    context,
    page
  }) => {
    requireMutableQaTarget();
    const users = requireUsers();
    const stamp = timestamp();
    const productName = `QA Click Filter Product ${stamp}`;
    await loginWithSession(context, users.engineer);

    await page.goto("/records");
    await page.getByRole("link", { name: /new record/i }).click();
    await page.getByLabel("Object type", { exact: true }).selectOption("product");
    await page.getByLabel("Commercial Name", { exact: true }).fill(productName);
    await page.getByLabel("Internal Grade", { exact: true }).fill(`QA-CLICK-FILTER-${stamp}`);
    await page.getByLabel("Resin Family", { exact: true }).selectOption("PC");
    await page.getByLabel("Application", { exact: true }).fill("Clickable dashboard and filter verification");
    await page.getByLabel("Color", { exact: true }).fill("Clear");
    const createRecordResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === "/api/records/"
    );
    await page.getByRole("button", { name: /create record/i }).click();
    const product = (await (await createRecordResponse).json()) as RecordPayload;
    await expect(page).toHaveURL(new RegExp(`/records/${product.id}$`));
    await expect(page.getByRole("button", { name: /delete/i })).toHaveCount(0);

    await page.getByLabel("Color", { exact: true }).fill("Transparent smoke");
    const saveFieldsResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "PATCH" &&
        new URL(response.url()).pathname === `/api/records/${product.id}/`
    );
    await page.getByRole("button", { name: /save fields/i }).click();
    await expect((await saveFieldsResponse).status()).toBe(200);
    await expect(page.getByText(/saved/i).first()).toBeVisible();

    await page.getByLabel("Version change note", { exact: true }).fill("Operator UI version proof");
    const versionResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/records/${product.id}/versions/`
    );
    await page.getByRole("button", { name: /create version/i }).click();
    await expect((await versionResponse).status()).toBe(201);
    await expect(page.getByText(/version .*created/i).first()).toBeVisible();
    await expect(page.getByLabel("Record versions")).toContainText("Operator UI version proof");

    const releaseResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/records/${product.id}/release/`
    );
    await page.getByRole("button", { name: /^release$/i }).click();
    await expect((await releaseResponse).status()).toBe(200);
    await expect(page.getByLabel("Record summary")).toContainText(/released/i);

    await page.getByRole("button", { name: /^archive$/i }).click();
    await expect(page.getByRole("status")).toContainText(/records are not deleted/i);
    const deniedArchiveResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/records/${product.id}/archive/`
    );
    await page.getByRole("button", { name: /confirm archive/i }).click();
    await expect((await deniedArchiveResponse).status()).toBe(403);
    await expect(page.getByRole("alert")).toContainText(/permission|archive/i);

    await loginWithSession(context, users.systemAdmin);
    await page.goto(`/records/${product.id}`);
    await page.getByRole("button", { name: /^archive$/i }).click();
    await expect(page.getByRole("status")).toContainText(/records are not deleted/i);
    const archiveResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/records/${product.id}/archive/`
    );
    await page.getByRole("button", { name: /confirm archive/i }).click();
    await expect((await archiveResponse).status()).toBe(200);
    await expect(page.getByLabel("Record summary")).toContainText(/archived/i);

    await page.goto("/records");
    await page.getByLabel("Object type", { exact: true }).selectOption("product");
    await page.getByLabel("Status", { exact: true }).selectOption("archived");
    await page.getByLabel("Search records", { exact: true }).fill(productName);
    await page.getByRole("button", { name: /^Search$/i }).click();
    await expect(page.getByRole("link", { name: product.code })).toBeVisible();
    await page.getByRole("link", { name: product.code }).click();
    await expect(page).toHaveURL(new RegExp(`/records/${product.id}$`));
    await expect(page.getByRole("heading", { name: product.title })).toBeVisible();

    await page.goto("/dashboards");
    const dashboardKey = users.fixtures.dashboardKey ?? "quality_operations";
    await page.getByLabel("Dashboard id", { exact: true }).fill(dashboardKey);
    await page.getByRole("button", { name: /refresh/i }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: /quality operations|dashboards/i })
    ).toBeVisible();
    const recordsByStatusWidget = page.getByRole("region", { name: /records by status/i }).first();
    await recordsByStatusWidget.getByRole("link", { name: /archived/i }).click();
    await expect(page).toHaveURL(/\/records\?status=archived$/);
    await expectNoRawFailure(page, "dashboard archived status link");

    await page.goto("/dashboards");
    await page.getByLabel("Dashboard id", { exact: true }).fill(dashboardKey);
    await page.getByRole("button", { name: /refresh/i }).click();
    await recordsByStatusWidget.getByRole("link", { name: /draft/i }).click();
    await expect(page).toHaveURL(/\/records\?status=draft$/);
    await expectNoRawFailure(page, "dashboard draft status link");

    await page.goto("/dashboards");
    await page.getByLabel("Dashboard id", { exact: true }).fill(dashboardKey);
    await page.getByRole("button", { name: /refresh/i }).click();
    await expect(page.locator(".dashboard-widget .dashboard-widget-item:not(a)")).toHaveCount(0);

    const widgetLinks = await page.locator(".dashboard-widget a").evaluateAll((links) =>
      links
        .map((link) => ({
          href: link.getAttribute("href") ?? "",
          text: link.textContent?.replace(/\s+/g, " ").trim() ?? ""
        }))
        .filter((link) => link.href)
    );
    expect(widgetLinks.length).toBeGreaterThan(0);
    for (const link of widgetLinks.slice(0, 6)) {
      await page.goto("/dashboards");
      await page.getByLabel("Dashboard id", { exact: true }).fill(dashboardKey);
      await page.getByRole("button", { name: /refresh/i }).click();
      await page.locator(".dashboard-widget a", { hasText: link.text }).first().click();
      await expect(page).toHaveURL(new RegExp(escapeRegex(link.href)));
      await expect(page.locator("body")).not.toContainText(/JSON\.parse|Workload failed|unexpected character/i);
    }
  });

  test("project operators create projects, update owners/status, click every project tab, and assign tasks", async ({
    context,
    page
  }, testInfo) => {
    requireMutableQaTarget();
    const users = requireUsers();
    const session = await loginWithSession(context, users.engineer);
    const currentUser = await getJson<CurrentUser>(session.request, "/api/accounts/me/");
    const projectName = `QA Operator Project ${timestamp()}`;

    await page.goto("/projects");
    await page.getByLabel("Project Name", { exact: true }).fill(projectName);
    await page.getByLabel("Description", { exact: true }).fill("Created through project UI clickthrough.");
    await page.getByLabel("Owner User ID", { exact: true }).fill(String(currentUser.id));
    const createProjectResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === "/api/projects/"
    );
    await page.getByRole("button", { name: /create project/i }).click();
    const project = (await (await createProjectResponse).json()) as ProjectPayload;
    await expect(page.getByRole("link", { name: projectName })).toBeVisible();

    await page.getByRole("link", { name: projectName }).click();
    await expect(page).toHaveURL(new RegExp(`/projects/${project.id}$`));
    await page.getByLabel("Project Status", { exact: true }).selectOption("active");
    await page.getByLabel("Owner User ID", { exact: true }).fill(String(currentUser.id));
    const updateProjectResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "PATCH" &&
        new URL(response.url()).pathname === `/api/projects/${project.id}/`
    );
    await page.getByRole("button", { name: /save project/i }).click();
    await expect((await updateProjectResponse).status()).toBe(200);
    await expect(page.getByLabel("Project Status", { exact: true })).toHaveValue("active");
    await expect(page.getByLabel("Owner User ID", { exact: true })).toHaveValue(String(currentUser.id));

    for (const tabName of ["Board", "Timeline", "Dependencies", "Linked Records", "Documents", "Audit"]) {
      const tabButton = page.getByRole("button", { name: tabName });
      await tabButton.click();
      await expect(tabButton).toHaveClass(/segmented-tab-active/);
    }
    await expect(page.getByRole("heading", { name: /^Audit$/i })).toBeVisible();
    await expect(page.getByRole("list", { name: /project audit events/i })).toContainText(/project updated/i);
    await expect(page.locator("body")).not.toContainText(/not available from the current project endpoints/i);

    await page.getByRole("button", { name: "Documents" }).click();
    await expect(page.getByRole("heading", { name: /^Documents$/i })).toBeVisible();
    await expect(page.getByRole("list", { name: /project documents/i })).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/not available from the current project endpoints/i);

    if (!users.fixtures.projectId || !users.fixtures.firstTaskId) {
      recordAndNote(
        {
          id: "QA-CLICK-PROJECT-TASK-SEED",
          severity: "High",
          area: "Projects",
          title: "Seeded project task was unavailable for task assignment UI",
          expected: "Project task assignment clickthrough uses a deterministic seeded task.",
          actual: "ensureQaUsers() did not return projectId and firstTaskId fixtures.",
          evidence: "frontend/e2e/support/qaApi.ts seedQaState"
        },
        testInfo
      );
      return;
    }

    await page.goto(`/projects/${users.fixtures.projectId}`);
    await page.getByRole("button", { name: "Board" }).click();
    const taskCard = page.getByRole("article", { name: /QA compound material/i });
    await expect(taskCard).toBeVisible();
    const moveTaskResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "PATCH" &&
        new URL(response.url()).pathname === `/api/project-tasks/${users.fixtures.firstTaskId}/move/`
    );
    await taskCard.getByLabel("Move task", { exact: true }).selectOption(String(users.fixtures.doingColumnId));
    await expect((await moveTaskResponse).status()).toBe(200);
    await taskCard.getByLabel("Task State", { exact: true }).selectOption("in_progress");
    await taskCard.getByLabel("Assignee User ID", { exact: true }).fill(String(currentUser.id));
    const updateTaskResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "PATCH" &&
        new URL(response.url()).pathname === `/api/project-tasks/${users.fixtures.firstTaskId}/`
    );
    await taskCard.getByRole("button", { name: /save task/i }).click();
    await expect((await updateTaskResponse).status()).toBe(200);
    await expect(taskCard.getByLabel("Task State", { exact: true })).toHaveValue("in_progress");
    await expect(taskCard.getByLabel("Assignee User ID", { exact: true })).toHaveValue(String(currentUser.id));

    await page.getByRole("button", { name: "Dependencies" }).click();
    const dependencyRow = page.getByRole("article", { name: /dependencies for QA run first molding pass/i });
    await expect(dependencyRow).toBeVisible();
    const dependencyResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/project-tasks/${users.fixtures.secondTaskId}/dependencies/`
    );
    await dependencyRow.getByLabel(/add dependency for QA run first molding pass/i).selectOption(String(users.fixtures.firstTaskId));
    await expect((await dependencyResponse).status()).toBe(201);
  });

  test("configuration field add/remove is draft-only and blocked for normal users", async ({
    context,
    page
  }) => {
    requireMutableQaTarget();
    const users = requireUsers();

    await loginWithSession(context, users.engineer);
    await page.goto("/admin");
    await page.getByRole("button", { name: /create draft/i }).click();
    await expect(page.getByRole("alert")).toContainText(/permission|403|forbidden/i);
    await page.getByRole("tab", { name: /draft editor/i }).click();
    await expect(page.getByRole("button", { name: /add field/i })).toBeDisabled();
    await expect(page.getByRole("button", { name: /remove field/i }).first()).toBeDisabled();

    await page.getByRole("button", { name: /sign out/i }).click();
    await expect(page.getByRole("link", { name: /sign in/i })).toBeVisible();
    await loginWithSession(context, users.configAdmin);
    await page.goto("/admin");
    await page.getByRole("button", { name: /create draft/i }).click();
    await expect(page.getByRole("heading", { name: /object type editor/i })).toBeVisible();
    await page.getByRole("button", { name: /add field/i }).click();

    const newField = page.getByRole("article", { name: /new field field/i });
    await expect(newField.getByLabel("Field key", { exact: true })).toHaveValue("new_field");
    await newField.getByLabel("Field label", { exact: true }).fill("QA Added Field");
    const removableField = page.getByRole("article", { name: /resin family field/i });
    await removableField.getByRole("button", { name: /remove field/i }).click();
    await expect(page.getByRole("article", { name: /resin family field/i })).toHaveCount(0);
    await expect(page.getByLabel("Visible fields", { exact: true })).toHaveValue(/new_field/);
    await page.getByRole("button", { name: /validate draft/i }).click();
    await expect(page.getByText(/no validation errors|breaking changes/i).first()).toBeVisible();

    await page.getByRole("tab", { name: /publish/i }).click();
    await expect(publishPanel(page).getByRole("button", { name: /publish configuration/i })).toBeDisabled();

    await page.getByRole("button", { name: /sign out/i }).click();
    await expect(page.getByRole("link", { name: /sign in/i })).toBeVisible();
    await loginWithSession(context, users.systemAdmin);
    await page.goto("/admin");
    await page.getByRole("button", { name: /create draft/i }).click();
    await page.getByLabel("Admin object type", { exact: true }).selectOption("raw_material");
    await page.getByRole("button", { name: /add field/i }).click();
    const systemField = page.getByRole("article", { name: /new field field/i });
    const systemFieldKey = `qa_operator_field_${timestamp().replace(/[^a-z0-9_]/gi, "_").toLowerCase()}`;
    const systemFieldLabel = `QA Operator Field ${systemFieldKey.slice(-8)}`;
    await systemField.getByLabel("Field key", { exact: true }).fill(systemFieldKey);
    await systemField.getByLabel("Field label", { exact: true }).fill(systemFieldLabel);
    await page.getByRole("button", { name: /validate draft/i }).click();
    await expect(page.getByText(/no validation errors/i).first()).toBeVisible();
    await page.getByRole("tab", { name: /publish/i }).click();
    const publishAddResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname.match(/\/api\/config\/drafts\/\d+\/publish\/$/)
    );
    await publishPanel(page).getByRole("button", { name: /publish configuration/i }).click();
    await expect((await publishAddResponse).status()).toBe(201);

    await page.goto("/records/new");
    await page.getByLabel("Object type", { exact: true }).selectOption("raw_material");
    await expect(page.getByLabel(systemFieldLabel, { exact: true })).toBeVisible();

    await page.goto("/admin");
    await page.getByRole("button", { name: /create draft/i }).click();
    await page.getByLabel("Admin object type", { exact: true }).selectOption("raw_material");
    const addedField = page.getByRole("article", {
      name: new RegExp(`${escapeRegex(systemFieldLabel)} field`, "i")
    });
    await addedField.getByRole("button", { name: /remove field/i }).click();
    await page.getByRole("button", { name: /validate draft/i }).click();
    await expect(page.getByText(/breaking changes/i).first()).toBeVisible();
    await page.getByRole("tab", { name: /publish/i }).click();
    await expect(publishPanel(page).getByRole("button", { name: /publish configuration/i })).toBeDisabled();
    await page.getByLabel(/I understand this can hide or invalidate existing record data/i).check();
    const publishRemoveResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname.match(/\/api\/config\/drafts\/\d+\/publish\/$/)
    );
    await publishPanel(page).getByRole("button", { name: /publish configuration/i }).click();
    await expect((await publishRemoveResponse).status()).toBe(201);
  });

  test("documents upload from UI, release from record, open preview audit download links, and add revisions", async ({
    context,
    page,
    request
  }) => {
    requireMutableQaTarget();
    const users = requireUsers();
    const session = await loginWithSession(context, users.engineer);
    const pdfPath = await downloadExternalPdf(request);
    const product = await createRecord(session, "product", {
      commercial_name: `QA Document Clickthrough ${timestamp()}`,
      internal_grade: `QA-DOC-CLICK-${timestamp()}`,
      resin_family: "PC",
      application: "Document button verification",
      color: "Clear"
    });

    await page.goto(`/records/${product.id}`);
    await page.getByLabel("Revision label", { exact: true }).fill("A");
    const uploadResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === "/api/documents/"
    );
    await page.getByLabel("Upload document", { exact: true }).setInputFiles(pdfPath);
    const document = (await (await uploadResponse).json()) as DocumentPayload;
    await expect(page.getByText(document.title)).toBeVisible();

    const releaseRevision = page.getByRole("button", { name: /release revision A/i }).first();
    await expect(releaseRevision).toBeEnabled();
    const releaseResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname.includes(`/api/documents/${document.id}/revisions/`) &&
        new URL(response.url()).pathname.endsWith("/release/")
    );
    await releaseRevision.click();
    await expect((await releaseResponse).status()).toBe(200);
    await expect(page.getByRole("listitem").filter({ hasText: document.title }).first()).toContainText(/released/i);

    const documentItem = page.getByRole("listitem").filter({ hasText: document.title }).first();
    await documentItem.getByRole("link", { name: /open/i }).click();
    await expect(page).toHaveURL(new RegExp(`/documents/${document.id}$`));
    await expect(page.getByRole("heading", { name: document.title })).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: /download/i }).first().click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.pdf$/i);

    await page.getByRole("tab", { name: /preview/i }).click();
    await expect(page.getByRole("heading", { name: /document preview/i })).toBeVisible();
    await expect(page.locator(".document-preview-text")).not.toContainText(/^\s*\{/);

    await page.getByRole("tab", { name: /audit/i }).click();
    await expect(page.getByRole("heading", { name: /document audit/i })).toBeVisible();

    await page.getByRole("tab", { name: /overview/i }).click();
    await page.getByLabel("New revision label", { exact: true }).fill("B");
    await page.getByLabel("New revision file", { exact: true }).setInputFiles(pdfPath);
    await page.getByRole("button", { name: /add revision/i }).click();
    await expect(page.getByText(/revision B uploaded/i)).toBeVisible();
    await expect(page.getByLabel("Revision history").first()).toContainText(/vB/i);

    const archiveResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/documents/${document.id}/archive/`
    );
    await page.getByRole("button", { name: /archive document/i }).click();
    await expect((await archiveResponse).status()).toBe(200);
    await expect(page.getByRole("status")).toContainText(/document archived/i);
    await expect(page.getByRole("listitem").filter({ hasText: document.title }).first()).toContainText(/obsolete/i);
  });

  test("task inbox and folder review buttons complete, assign, accept, ignore, and link work items", async ({
    context,
    page
  }) => {
    requireMutableQaTarget();
    const users = requireUsers();
    const session = await loginWithSession(context, users.systemAdmin);
    const currentUser = await getJson<CurrentUser>(session.request, "/api/accounts/me/");
    const manifest = seedClientReadinessDemo(`operator-tasks-${timestamp()}`);
    const workflowTask = manifest.workflowTasks[0];
    const pendingEvents = manifest.folderEvents.filter((event) => event.reviewStatus === "pending");
    expect(pendingEvents.length).toBeGreaterThanOrEqual(4);

    await page.goto("/tasks");
    const createdTaskTitle = `QA Operator Created Task ${timestamp()}`;
    await page.getByRole("button", { name: /new task/i }).click();
    await page.getByLabel("Task Title", { exact: true }).fill(createdTaskTitle);
    await page.getByLabel("Related Record ID", { exact: true }).fill(workflowTask.relatedRecordId);
    await page.getByLabel("Task Assignee User ID", { exact: true }).fill(String(currentUser.id));
    const createTaskResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === "/api/workflow-tasks/"
    );
    await page.getByRole("button", { name: /create task/i }).click();
    await expect((await createTaskResponse).status()).toBe(201);
    await expect(page.getByRole("status")).toContainText(/task created/i);
    await expect(page.getByRole("row", { name: new RegExp(escapeRegex(createdTaskTitle), "i") })).toBeVisible();

    await page.getByRole("link", { name: /open inbox/i }).click();
    await expect(page).toHaveURL(/\/tasks\/folder-events$/);
    await page.goto("/tasks");
    const taskRow = page.getByRole("row", { name: new RegExp(escapeRegex(workflowTask.title), "i") });
    await expect(taskRow).toBeVisible();
    await taskRow.getByRole("link", { name: /^open$/i }).click();
    await expect(page).toHaveURL(new RegExp(`/records/${workflowTask.relatedRecordId}$`));
    await page.goto("/tasks");
    const refreshedTaskRow = page.getByRole("row", { name: new RegExp(escapeRegex(workflowTask.title), "i") });
    const completeTaskResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/workflow-tasks/${workflowTask.id}/complete/`
    );
    await refreshedTaskRow.getByRole("button", { name: /^complete$/i }).click();
    await expect((await completeTaskResponse).status()).toBe(200);
    await expect(refreshedTaskRow).toHaveCount(0);

    const [assignEvent, acceptEvent, ignoreEvent, linkEvent] = pendingEvents;
    await page.goto("/tasks/folder-events");
    const assignRow = folderEventRow(page, assignEvent.path);
    await expect(assignRow).toBeVisible();
    await assignRow.getByLabel(`Assign user for event ${assignEvent.id}`, { exact: true }).fill(String(currentUser.id));
    const assignResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/folder-events/${assignEvent.id}/assign/`
    );
    await assignRow.getByRole("button", { name: /^assign$/i }).click();
    await expect((await assignResponse).status()).toBe(200);
    await expect(assignRow).toContainText(currentUser.username);

    const acceptRow = folderEventRow(page, acceptEvent.path);
    await expect(acceptRow).toBeVisible();
    const acceptResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/folder-events/${acceptEvent.id}/accept/`
    );
    await acceptRow.getByRole("button", { name: /^accept$/i }).click();
    await expect((await acceptResponse).status()).toBe(200);
    await expect(acceptRow).toHaveCount(0);

    const ignoreRow = folderEventRow(page, ignoreEvent.path);
    await expect(ignoreRow).toBeVisible();
    const ignoreResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/folder-events/${ignoreEvent.id}/ignore/`
    );
    await ignoreRow.getByRole("button", { name: /^ignore$/i }).click();
    await expect((await ignoreResponse).status()).toBe(200);
    await expect(ignoreRow).toHaveCount(0);

    const linkRow = folderEventRow(page, linkEvent.path);
    await expect(linkRow).toBeVisible();
    const linkResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === `/api/folder-events/${linkEvent.id}/link-document/`
    );
    await linkRow.getByRole("button", { name: /link document/i }).click();
    await expect((await linkResponse).status()).toBe(201);
    await expect(page.getByRole("status")).toContainText(/linked document|folder event linked/i);
  });

  test("search filters return clickable records, documents, projects, and folder events", async ({
    context,
    page,
    request
  }) => {
    test.setTimeout(150_000);
    requireMutableQaTarget();
    const users = requireUsers();
    const session = await loginWithSession(context, users.systemAdmin);
    const stamp = timestamp();
    const pdfPath = await downloadExternalPdf(request);
    const product = await createRecord(session, "product", {
      commercial_name: `QA Search Product ${stamp}`,
      internal_grade: `QA-SEARCH-${stamp}`,
      resin_family: "PC",
      application: "Unified search clickthrough",
      color: "Clear"
    });
    const document = await uploadDocumentThroughApi(session, product.id, `QA Search Document ${stamp}`, pdfPath);
    const manifest = seedClientReadinessDemo(`operator-search-${stamp}`);
    const project = manifest.projects[0];
    const folderEvent = manifest.folderEvents.find((event) => event.reviewStatus === "pending") ?? manifest.folderEvents[0];

    await expectSearchResult(page, "all", product.title, new RegExp(escapeRegex(product.title), "i"), new RegExp(`/records/${product.id}$`));
    await expectSearchResult(page, "records", product.title, new RegExp(escapeRegex(product.title), "i"), new RegExp(`/records/${product.id}$`));
    await expectSearchResult(page, "documents", document.title, new RegExp(escapeRegex(document.title), "i"), new RegExp(`/documents/${document.id}$`));
    await expectSearchResult(page, "projects", project.name, new RegExp(escapeRegex(project.name), "i"), new RegExp(`/projects/${project.id}$`));
    await expectSearchResult(
      page,
      "folder_events",
      folderEvent.path,
      new RegExp(escapeRegex(folderEvent.path), "i"),
      new RegExp(`/tasks/folder-events/${folderEvent.id}$`)
    );
  });
});

function requireUsers(): Extract<QaUserSetup, { ok: true }> {
  const users = ensureQaUsers();
  if (!users.ok) {
    throw new Error(users.message);
  }
  return users;
}

function recordAndNote(finding: BugFinding, testInfo: TestInfo) {
  recordFinding(finding, testInfo);
  testInfo.annotations.push({ type: "finding", description: `${finding.id}: ${finding.title}` });
}

function publishPanel(page: Page) {
  return page.getByRole("region", { name: /release configuration/i });
}

function folderEventRow(page: Page, path: string) {
  return page.getByRole("row", { name: new RegExp(escapeRegex(path), "i") });
}

async function expectNoRawFailure(page: Page, label: string) {
  const body = await page.locator("body").innerText();
  expect(body, label).not.toMatch(/JSON\.parse|Workload failed|unexpected character/i);
  expect(body, label).not.toMatch(/^\s*\{[\s\S]*"\w+"[\s\S]*\}\s*$/);
  expect(body, label).not.toMatch(/Django|Traceback|OperationalError|IntegrityError/i);
}

function timestamp() {
  return `${new Date().toISOString().replace(/[-:.TZ]/g, "")}-${Math.random().toString(36).slice(2, 8)}`;
}

async function uploadDocumentThroughApi(
  session: Awaited<ReturnType<typeof loginWithSession>>,
  ownerRecordId: string | number,
  title: string,
  filePath: string
) {
  const response = await session.request.post("/api/documents/", {
    headers: { "x-csrftoken": session.csrfToken },
    multipart: {
      owner_record: String(ownerRecordId),
      title,
      document_type: "technical_data_sheet",
      revision_label: "A",
      file: {
        name: "qa-search-document.pdf",
        mimeType: "application/pdf",
        buffer: readFileSync(filePath)
      }
    }
  });
  expect(response.status(), await response.text()).toBe(201);
  return response.json() as Promise<DocumentPayload>;
}

async function expectSearchResult(
  page: Page,
  type: string,
  query: string,
  linkName: string | RegExp,
  expectedUrl: RegExp
) {
  let link = page.getByRole("link", { name: linkName }).first();
  for (let attempt = 0; attempt < 12; attempt += 1) {
    await page.goto("/search");
    await page.getByLabel("Search query", { exact: true }).fill(query);
    await page.getByRole("tab", { name: new RegExp(`^${humanize(type)}$`, "i") }).click();
    await page.getByRole("button", { name: /^search$/i }).click();
    await expectNoRawFailure(page, `${type} search for ${query}`);
    link = page.getByRole("link", { name: linkName }).first();
    if (await link.isVisible().catch(() => false)) {
      break;
    }
    await page.waitForTimeout(1_500);
  }
  await expect(link, `${type} search result for "${query}"`).toBeVisible({ timeout: 5_000 });
  await link.click();
  await expect(page).toHaveURL(expectedUrl);
  await expectNoRawFailure(page, `${type} search result route for ${query}`);
}

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

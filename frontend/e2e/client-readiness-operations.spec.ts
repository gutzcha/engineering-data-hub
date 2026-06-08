import { expect, test, type APIResponse, type BrowserContext, type TestInfo } from "@playwright/test";

import {
  createRecord,
  ensureQaUsers,
  getJson,
  loginWithSession,
  postJson,
  requireHealthyStack,
  requireMutableQaTarget,
  type AuthenticatedSession,
  type QaCredentials,
  type QaUserSetup
} from "./support/qaApi";
import { ensureQaReport, recordFinding, type BugFinding } from "./support/qaReport";
import { readinessGate } from "./support/strictReadiness";

type RelationshipPayload = {
  id: number;
  source_record: string;
  target_record: string;
  relationship_type_key: string;
  data: Record<string, unknown>;
};

type AuditPayload = {
  results: Array<{
    id: number;
    action: string;
    object_type: string;
    object_id: string;
  }>;
};

type SavedView = {
  id: number;
  name: string;
};

type SavedViewResults = {
  count: number;
  results: Array<Record<string, unknown> & { id?: string }>;
};

type DashboardPayload = {
  id: number;
  name: string;
  widgets: Array<{
    id: number;
    title: string;
    data?: { items?: unknown[] };
  }>;
};

type ProjectBoard = {
  project: { id: string; name: string };
  columns: Array<{
    id: number;
    title: string;
    tasks: Array<{ id: number; column: number | null; title: string }>;
  }>;
};

type ProjectTimeline = {
  project: { id: string; name: string };
  tasks: Array<{ id: number; title: string }>;
  dependencies: Array<{ task: number; depends_on: number }>;
};

type ProjectTask = {
  id: number;
  column: number | null;
  sort_order: number;
};

type ImportJob = {
  id: number;
  state: string;
};

type ImportDryRun = {
  summary: {
    create: number;
    update: number;
    errors: number;
  };
  error_rows?: unknown[];
};

type ApplyResult = {
  created: number;
  updated: number;
};

type BackupManifest = {
  backup_id: string;
  state: string;
};

const staticAuthenticatedRoutes = [
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
    readinessGate(!health.ok, health.message);
    const users = ensureQaUsers();
    readinessGate(!users.ok, users.message);
    ensureQaReport();
  });

  test("authenticated visible routes load without client console failures", async ({
    context,
    page
  }, testInfo) => {
    const users = requireUsers();
    const session = await loginWithSession(context, users.systemAdmin);
    const product = await createRecord(session, "product", productData(`Route Health ${stamp()}`));
    const routes = [
      ...staticAuthenticatedRoutes,
      `/records/${product.id}`,
      ...(users.fixtures.projectId ? [`/projects/${users.fixtures.projectId}`] : [])
    ];

    if (!users.fixtures.projectId) {
      recordAndSoftFail(
        {
          id: "QA-OPS-PROJECT-ROUTE-SEED",
          severity: "Medium",
          area: "Route health",
          title: "Project detail route could not use a seeded project",
          expected: "Operations route health includes a real seeded /projects/:projectId route.",
          actual: "No projectId was available from QA fixture seeding.",
          evidence: "ensureQaUsers().fixtures.projectId"
        },
        testInfo
      );
    }

    const failures: string[] = [];
    let currentRoute = "";
    page.on("console", (message) => {
      if (message.type() === "error") {
        failures.push(`${currentRoute}: ${message.text()}`);
      }
    });
    page.on("pageerror", (error) => {
      failures.push(`${currentRoute}: ${error.message}`);
    });

    for (const route of routes) {
      currentRoute = route;
      await page.goto(route);
      await expect(page.locator("body"), route).toBeVisible();
      await page.waitForLoadState("domcontentloaded");
      await page.waitForTimeout(250);

      const bodyText = await page.locator("body").innerText();
      if (route === "/admin" && /Django (administration|site admin)/i.test(bodyText)) {
        recordAndSoftFail(
          {
            id: "QA-OPS-ADMIN-ROUTE",
            severity: "High",
            area: "Route health",
            title: "Direct /admin route served Django admin instead of the React workspace",
            expected: "Authenticated /admin route health serves the React admin configuration workspace.",
            actual: "The direct /admin body contained Django admin text.",
            evidence: route
          },
          testInfo
        );
      }
    }

    const failureText = failures.join("\n");
    if (failureText) {
      recordAndSoftFail(
        {
          id: "QA-OPS-ROUTE-CONSOLE",
          severity: /JSON\.parse|Workload failed/i.test(failureText) ? "High" : "Medium",
          area: "Route health",
          title: "Authenticated routes emitted browser console errors",
          expected: "Every visible authenticated route loads without console errors, including JSON.parse and Workload failed failures.",
          actual: truncate(failureText),
          evidence: "frontend/e2e/client-readiness-operations.spec.ts route health"
        },
        testInfo
      );
    }

    expect.soft(failureText).not.toMatch(/JSON\.parse|Workload failed|unexpected character/i);
    expect.soft(failures, failureText).toEqual([]);
  });

  test("relationships create, reject invalid targets, delete, audit, and search through the UI", async ({
    context,
    page
  }, testInfo) => {
    requireMutableQaTarget();
    const users = requireUsers();
    const session = await loginWithSession(context, users.engineer);
    const runStamp = stamp();

    const supplier = await createRecord(session, "supplier", supplierData(runStamp));
    const rawMaterial = await createRecord(session, "raw_material", rawMaterialData(runStamp, supplier.id));
    const product = await createRecord(session, "product", productData(`Graph Product ${runStamp}`));
    const productSpec = await createRecord(session, "product_spec", productSpecData(runStamp, product.id));

    const relationship = await postJson<RelationshipPayload>(
      session,
      "/api/relationships/",
      {
        source_record: product.id,
        target_record: rawMaterial.id,
        relationship_type_key: "product_uses_material",
        data: { basis: "QA primary resin" }
      },
      201
    );

    const invalidTarget = await postJson<Record<string, unknown>>(
      session,
      "/api/relationships/",
      {
        source_record: product.id,
        target_record: productSpec.id,
        relationship_type_key: "product_uses_material",
        data: { basis: "QA invalid target gate" }
      },
      400
    );
    expect(JSON.stringify(invalidTarget)).toMatch(/target_record|raw_material/i);

    const graph = await getJson<{ nodes: unknown[]; edges: unknown[] }>(
      session.request,
      `/api/records/${product.id}/graph/`
    );
    expect(graph.nodes.length).toBeGreaterThanOrEqual(2);
    expect(graph.edges.length).toBeGreaterThanOrEqual(1);

    await expectAuditEvent(session, relationship.id, "relationship.created", testInfo);

    const deleteResponse = await session.request.delete(`/api/relationships/${relationship.id}/`, {
      headers: { "x-csrftoken": session.csrfToken }
    });
    expect(deleteResponse.status()).toBe(204);
    await expectAuditEvent(session, relationship.id, "relationship.deleted", testInfo);

    await page.goto("/search");
    await page.getByLabel(/search query/i).fill(product.title);
    await page.getByRole("button", { name: /^Search$/i }).click();
    try {
      await expect(page.getByText(product.title).first()).toBeVisible({ timeout: 20_000 });
    } catch {
      recordAndSoftFail(
        {
          id: "QA-OPS-SEARCH-RESULTS",
          severity: "Medium",
          area: "Search",
          title: "Created QA record was not returned through the Search query UI",
          expected: "Search via the accessible Search query field returns newly indexed QA records.",
          actual: `No visible result for ${product.title}. Search may be disabled, unindexed, or permission-filtered.`,
          evidence: "/search using getByLabel(/search query/i)"
        },
        testInfo
      );
    }
  });

  test("saved views return result rows and seeded dashboard key loads widgets", async ({
    context
  }, testInfo) => {
    const users = requireUsers();
    const session = await loginWithSession(context, users.engineer);
    const runStamp = stamp();
    const product = await createRecord(session, "product", productData(`Saved View Product ${runStamp}`));

    const savedView = await postJson<SavedView>(
      session,
      "/api/saved-views/",
      {
        name: `QA Saved View ${runStamp}`,
        filters: [
          { type: "object_type", value: "product" },
          {
            type: "field_contains",
            field: "commercial_name",
            value: String(product.data.commercial_name)
          }
        ],
        columns: ["code", "title", "status", "data.commercial_name"],
        sort: ["code"]
      },
      201
    );

    const results = await getJson<SavedViewResults>(
      session.request,
      `/api/saved-views/${savedView.id}/results/?limit=10`
    );
    if (!results.results.some((row) => row.id === product.id)) {
      recordAndSoftFail(
        {
          id: "QA-OPS-SAVED-VIEW-RESULTS",
          severity: "Medium",
          area: "Dashboards",
          title: "Saved view did not return the seeded QA product",
          expected: "Saved view results include rows matching the saved filters.",
          actual: `Saved view ${savedView.id} returned ${results.count} rows without ${product.id}.`,
          evidence: `/api/saved-views/${savedView.id}/results/?limit=10`
        },
        testInfo
      );
    }

    const dashboardKey = users.fixtures.dashboardKey ?? "quality_operations";
    const dashboardResponse = await session.request.get(`/api/dashboards/${dashboardKey}/`);
    if (dashboardResponse.status() >= 400) {
      await recordControlledGap(dashboardResponse, {
        id: "QA-OPS-DASHBOARD-SEED",
        severity: "Medium",
        area: "Dashboards",
        title: "Seeded operations dashboard key is unavailable",
        expected: "The seeded quality_operations dashboard key returns dashboard widgets.",
        actual: `GET /api/dashboards/${dashboardKey}/ returned ${dashboardResponse.status()}.`,
        evidence: `/api/dashboards/${dashboardKey}/`
      }, testInfo);
      return;
    }

    const dashboard = await parseJson<DashboardPayload>(dashboardResponse, 200);
    expect(dashboard.widgets.length).toBeGreaterThan(0);
  });

  test("seeded project workload, board, timeline, task move, and dependency gates work", async ({
    context
  }, testInfo) => {
    requireMutableQaTarget();
    const users = requireUsers();
    const session = await loginWithSession(context, users.engineer);
    const fixtures = users.fixtures;
    const missingFixture = [
      "projectId",
      "doingColumnId",
      "firstTaskId",
      "secondTaskId"
    ].find((key) => !fixtures[key as keyof typeof fixtures]);

    if (missingFixture) {
      recordAndSoftFail(
        {
          id: "QA-OPS-PROJECT-SEED",
          severity: "High",
          area: "Projects",
          title: "Seeded project fixture IDs are unavailable",
          expected: "Project workload, board, timeline, move, and dependency gates use deterministic seeded fixture IDs.",
          actual: `Missing fixture field: ${missingFixture}.`,
          evidence: "ensureQaUsers().fixtures"
        },
        testInfo
      );
      return;
    }

    const projectId = fixtures.projectId as string;
    const doingColumnId = fixtures.doingColumnId as number;
    const firstTaskId = fixtures.firstTaskId as number;
    const secondTaskId = fixtures.secondTaskId as number;

    const workload = await getJson<Array<{ username: string; open_tasks: number }>>(
      session.request,
      "/api/projects/workload/"
    );
    expect(Array.isArray(workload)).toBe(true);

    const board = await getJson<ProjectBoard>(session.request, `/api/projects/${projectId}/board/`);
    expect(board.columns.flatMap((column) => column.tasks).some((task) => task.id === firstTaskId)).toBe(true);

    const timeline = await getJson<ProjectTimeline>(
      session.request,
      `/api/projects/${projectId}/timeline/`
    );
    expect(timeline.tasks.some((task) => task.id === firstTaskId)).toBe(true);

    const moved = await patchJson<ProjectTask>(session, `/api/project-tasks/${firstTaskId}/move/`, {
      column: doingColumnId,
      sort_order: 0
    });
    expect(moved.column).toBe(doingColumnId);

    const dependency = await postJson<{ task: number; depends_on: number }>(
      session,
      `/api/project-tasks/${secondTaskId}/dependencies/`,
      { depends_on: firstTaskId },
      201
    );
    expect(dependency.task).toBe(secondTaskId);
    expect(dependency.depends_on).toBe(firstTaskId);

    const selfCycle = await session.request.post(`/api/project-tasks/${firstTaskId}/dependencies/`, {
      headers: {
        "content-type": "application/json",
        "x-csrftoken": session.csrfToken
      },
      data: { depends_on: firstTaskId }
    });
    await parseJson(selfCycle, 400);

    const circular = await session.request.post(`/api/project-tasks/${firstTaskId}/dependencies/`, {
      headers: {
        "content-type": "application/json",
        "x-csrftoken": session.csrfToken
      },
      data: { depends_on: secondTaskId }
    });
    await parseJson(circular, 400);
  });

  test("import multipart CSV dry-run and apply creates product records", async ({
    context
  }, testInfo) => {
    requireMutableQaTarget();
    const users = requireUsers();
    const session = await loginWithSession(context, users.engineer);
    const runStamp = stamp();
    const csv = [
      "Commercial Name,Internal Grade,Resin Family,Application",
      `"QA Imported Product ${runStamp}","QA-IMP-${runStamp}","PC","Client-readiness import"`
    ].join("\n");

    const jobResponse = await session.request.post("/api/imports/jobs/", {
      headers: { "x-csrftoken": session.csrfToken },
      multipart: {
        target_object_type: "product",
        mapping: JSON.stringify({
          columns: {
            "Commercial Name": "commercial_name",
            "Internal Grade": "internal_grade",
            "Resin Family": "resin_family",
            Application: "application"
          }
        }),
        source_file: {
          name: `qa-import-${runStamp}.csv`,
          mimeType: "text/csv",
          buffer: Buffer.from(csv, "utf-8")
        }
      }
    });
    if (jobResponse.status() >= 400) {
      await recordControlledGap(jobResponse, {
        id: "QA-OPS-IMPORT-JOB",
        severity: "High",
        area: "Imports",
        title: "Multipart CSV import job could not be created",
        expected: "A multipart CSV upload creates an import job for product records.",
        actual: `Import job creation returned HTTP ${jobResponse.status()}.`,
        evidence: "/api/imports/jobs/"
      }, testInfo);
      return;
    }
    const job = await parseJson<ImportJob>(jobResponse, 201);

    const dryRunResponse = await session.request.post(`/api/imports/jobs/${job.id}/dry-run/`, {
      headers: {
        "content-type": "application/json",
        "x-csrftoken": session.csrfToken
      },
      data: {}
    });
    if (dryRunResponse.status() >= 400) {
      await recordControlledGap(dryRunResponse, {
        id: "QA-OPS-IMPORT-DRY-RUN-ENDPOINT",
        severity: "High",
        area: "Imports",
        title: "Multipart CSV import dry-run endpoint did not complete",
        expected: "A created import job can be dry-run before apply.",
        actual: `Import dry-run returned HTTP ${dryRunResponse.status()}.`,
        evidence: `/api/imports/jobs/${job.id}/dry-run/`
      }, testInfo);
      return;
    }
    const dryRun = await parseJson<ImportDryRun>(dryRunResponse, 200);
    if (dryRun.summary.errors > 0 || dryRun.summary.create !== 1) {
      recordAndSoftFail(
        {
          id: "QA-OPS-IMPORT-DRY-RUN",
          severity: "High",
          area: "Imports",
          title: "Multipart CSV import dry-run did not produce one clean create",
          expected: "A valid product CSV dry-run reports one create and zero errors.",
          actual: JSON.stringify(dryRun.summary),
          evidence: `/api/imports/jobs/${job.id}/dry-run/`
        },
        testInfo
      );
      return;
    }

    const applyResponse = await session.request.post(`/api/imports/jobs/${job.id}/apply/`, {
      headers: {
        "content-type": "application/json",
        "x-csrftoken": session.csrfToken
      },
      data: { create_managed_folders: false }
    });
    if (applyResponse.status() >= 400) {
      await recordControlledGap(applyResponse, {
        id: "QA-OPS-IMPORT-APPLY-ENDPOINT",
        severity: "High",
        area: "Imports",
        title: "Multipart CSV import apply endpoint did not complete",
        expected: "A clean import dry-run can be applied to create records.",
        actual: `Import apply returned HTTP ${applyResponse.status()}.`,
        evidence: `/api/imports/jobs/${job.id}/apply/`
      }, testInfo);
      return;
    }
    const applied = await parseJson<ApplyResult>(applyResponse, 200);
    expect(applied.created).toBe(1);
    expect(applied.updated).toBe(0);
  });

  test("records, audit, and project-status XLSX exports download controlled workbooks", async ({
    context
  }, testInfo) => {
    const users = requireUsers();
    const session = await loginWithSession(context, users.engineer);

    await expectXlsx(
      session.request.get("/api/exports/records/product.xlsx"),
      "records export",
      "/api/exports/records/product.xlsx",
      testInfo
    );
    await expectXlsx(
      session.request.get("/api/exports/audit.xlsx"),
      "audit export",
      "/api/exports/audit.xlsx",
      testInfo
    );
    await expectXlsx(
      session.request.get("/api/exports/project-status.xlsx"),
      "project status export",
      "/api/exports/project-status.xlsx",
      testInfo
    );
  });

  test("backups can be listed, created, and retrieved by system admin", async ({
    context
  }, testInfo) => {
    requireMutableQaTarget();
    const users = requireUsers();
    const session = await loginOrFinding(
      context,
      users.systemAdmin,
      {
        id: "QA-OPS-BACKUP-ADMIN-LOGIN",
        severity: "High",
        area: "Backups",
        title: "System admin backup credentials are unavailable",
        expected: "Seeded system admin can authenticate and exercise backup endpoints.",
        actual: "System admin login failed.",
        evidence: "E2E_SYSTEM_ADMIN_USERNAME or ALLOW_E2E_USER_SEEDING"
      },
      testInfo
    );
    if (!session) {
      return;
    }

    const list = await parseJson<{ results: BackupManifest[] }>(
      await session.request.get("/api/backups/"),
      200
    );
    expect(Array.isArray(list.results)).toBe(true);

    const backupId = `qa-ops-${stamp()}`;
    const createResponse = await session.request.post("/api/backups/", {
      headers: {
        "content-type": "application/json",
        "x-csrftoken": session.csrfToken
      },
      data: { backup_id: backupId }
    });

    if (createResponse.status() >= 400) {
      await recordControlledGap(createResponse, {
        id: "QA-OPS-BACKUP-CREATE",
        severity: "High",
        area: "Backups",
        title: "System admin backup creation did not complete",
        expected: "System admin can create a backup manifest with database, media, config, and audit exports.",
        actual: `Backup creation returned HTTP ${createResponse.status()}.`,
        evidence: "/api/backups/"
      }, testInfo);
      return;
    }

    const manifest = await parseJson<BackupManifest>(createResponse, 201);
    expect(manifest.backup_id).toBe(backupId);
    expect(["completed", "running"]).toContain(manifest.state);

    const detail = await parseJson<BackupManifest>(
      await session.request.get(`/api/backups/${backupId}/`),
      200
    );
    expect(detail.backup_id).toBe(backupId);
  });

  test("folder events and workflow tasks return controlled JSON for authenticated users", async ({
    context
  }, testInfo) => {
    const users = requireUsers();
    const session = await loginWithSession(context, users.engineer);

    await expectControlledJson(
      await session.request.get("/api/folder-events/?review_status=pending"),
      "/api/folder-events/?review_status=pending",
      testInfo
    );
    await expectControlledJson(
      await session.request.get("/api/workflow-tasks/?state=open"),
      "/api/workflow-tasks/?state=open",
      testInfo
    );
  });
});

async function patchJson<T>(
  session: AuthenticatedSession,
  url: string,
  data: unknown,
  expectedStatus = 200
) {
  requireMutableQaTarget();
  const response = await session.request.patch(url, {
    headers: {
      "content-type": "application/json",
      "x-csrftoken": session.csrfToken
    },
    data
  });
  return parseJson<T>(response, expectedStatus);
}

async function expectAuditEvent(
  session: AuthenticatedSession,
  relationshipId: number,
  action: "relationship.created" | "relationship.deleted",
  testInfo: TestInfo
) {
  const audit = await getJson<AuditPayload>(
    session.request,
    `/api/audit/?action=${action}&object_type=relationship&object_id=${relationshipId}&limit=20`
  );
  if (!audit.results.some((event) => event.action === action)) {
    recordAndSoftFail(
      {
        id: `QA-OPS-${action.replace(/[._]+/g, "-").toUpperCase()}`,
        severity: "High",
        area: "Relationships",
        title: `${action} audit event was not visible`,
        expected: "Relationship create and delete actions are captured in the authenticated audit timeline.",
        actual: `No ${action} event was returned for relationship ${relationshipId}.`,
        evidence: `/api/audit/?action=${action}&object_type=relationship&object_id=${relationshipId}`
      },
      testInfo
    );
  }
}

async function expectXlsx(
  responsePromise: Promise<APIResponse>,
  label: string,
  endpoint: string,
  testInfo: TestInfo
) {
  const response = await responsePromise;
  const contentType = response.headers()["content-type"] ?? "";
  if (
    response.status() !== 200 ||
    !contentType.includes("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
  ) {
    recordAndSoftFail(
      {
        id: `QA-OPS-XLSX-${slug(endpoint)}`,
        severity: "High",
        area: "Exports",
        title: `${label} did not download as an XLSX workbook`,
        expected: "Records, audit, and project-status exports return XLSX workbooks to authenticated users.",
        actual: `HTTP ${response.status()} with content-type ${contentType || "none"}.`,
        evidence: endpoint
      },
      testInfo
    );
    return;
  }
  const body = await response.body();
  expect(body.length, label).toBeGreaterThan(100);
  expect(body.subarray(0, 2).toString("utf-8"), label).toBe("PK");
}

async function expectControlledJson(response: APIResponse, endpoint: string, testInfo: TestInfo) {
  const contentType = response.headers()["content-type"] ?? "";
  if (!contentType.includes("application/json")) {
    recordAndSoftFail(
      {
        id: `QA-OPS-CONTROLLED-JSON-${slug(endpoint)}`,
        severity: "High",
        area: "Operations API",
        title: `${endpoint} did not return controlled JSON`,
        expected: "Folder event and workflow task endpoints return JSON responses for authenticated users.",
        actual: `HTTP ${response.status()} with content-type ${contentType || "none"}.`,
        evidence: endpoint
      },
      testInfo
    );
    return;
  }
  if (response.status() >= 400) {
    recordAndSoftFail(
      {
        id: `QA-OPS-AUTHENTICATED-${slug(endpoint)}`,
        severity: response.status() >= 500 ? "High" : "Medium",
        area: "Operations API",
        title: `${endpoint} rejected an authenticated QA user`,
        expected: "Authenticated QA users receive successful JSON for folder events and workflow task inboxes.",
        actual: `HTTP ${response.status()}.`,
        evidence: endpoint
      },
      testInfo
    );
  }
}

async function recordControlledGap(
  response: APIResponse,
  finding: BugFinding,
  testInfo: TestInfo
) {
  const contentType = response.headers()["content-type"] ?? "";
  const body = await response.text();
  recordAndSoftFail(
    {
      ...finding,
      actual: `${finding.actual} Content-Type: ${contentType || "none"}. Body: ${truncate(body)}`
    },
    testInfo
  );
  expect.soft(contentType, finding.id).toContain("application/json");
}

async function parseJson<T>(response: APIResponse, expectedStatus: number) {
  const body = await response.text();
  expect(response.status(), body).toBe(expectedStatus);
  expect(response.headers()["content-type"] ?? "", body).toContain("application/json");
  return JSON.parse(body) as T;
}

async function loginOrFinding(
  context: BrowserContext,
  credentials: QaCredentials,
  finding: BugFinding,
  testInfo: TestInfo
) {
  try {
    return await loginWithSession(context, credentials);
  } catch (error) {
    recordAndSoftFail(
      {
        ...finding,
        actual: `${finding.actual} ${error instanceof Error ? error.message : String(error)}`
      },
      testInfo
    );
    return null;
  }
}

function requireUsers(): Extract<QaUserSetup, { ok: true }> {
  const users = ensureQaUsers();
  if (!users.ok) {
    throw new Error(users.message);
  }
  return users;
}

function recordAndSoftFail(finding: BugFinding, testInfo: TestInfo) {
  recordFinding(finding, testInfo);
  testInfo.annotations.push({ type: "finding", description: `${finding.id}: ${finding.title}` });
  expect.soft(false, `${finding.id}: ${finding.title}`).toBe(true);
}

function productData(name: string) {
  return {
    commercial_name: `QA ${name}`,
    internal_grade: `QA-${stamp()}`,
    resin_family: "PC",
    application: "Client-readiness operations",
    color: "Natural"
  };
}

function supplierData(runStamp: string) {
  return {
    supplier_name: `QA Resin Supplier ${runStamp}`,
    supplier_code: `QA-SUP-${runStamp}`,
    approved_status: "Approved"
  };
}

function rawMaterialData(runStamp: string, supplierId: string) {
  return {
    supplier_material_code: `QA-RM-${runStamp}`,
    material_family: "Base Resin",
    supplier: supplierId,
    melt_flow_index: 14,
    density: 0.91,
    color: "Natural"
  };
}

function productSpecData(runStamp: string, productId: string) {
  return {
    spec_number: `QA-SPEC-${runStamp}`,
    product: productId,
    revision: "A",
    effective_date: "2026-06-08",
    release_notes: "Operations relationship invalid-target gate."
  };
}

function stamp() {
  const time = new Date().toISOString().replace(/[-:.TZ]/g, "");
  return `${time}-${Math.random().toString(36).slice(2, 8)}`;
}

function slug(value: string) {
  return value.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toUpperCase();
}

function truncate(value: string, maxLength = 800) {
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
}

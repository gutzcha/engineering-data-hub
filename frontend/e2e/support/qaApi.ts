import { expect, type APIRequestContext, type APIResponse, type BrowserContext } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { plasticPdfManifest, type PlasticPdfSource } from "./plasticPdfManifest";

export const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "https://plastic-hub.local";
export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
export const DEFAULT_PDF_URL =
  process.env.QA_EXTERNAL_PDF_URL ?? "https://plastic-craft.com/content/SDS/polycarbonate.pdf";
const COMPOSE_PROJECT_NAME =
  process.env.QA_COMPOSE_PROJECT_NAME ?? process.env.COMPOSE_PROJECT_NAME ?? "plastic-engineering-data-hub";

export type QaCredentials = {
  username: string;
  password: string;
};

export type QaFixtures = {
  projectId?: string;
  projectRecordId?: string;
  todoColumnId?: number;
  doingColumnId?: number;
  firstTaskId?: number;
  secondTaskId?: number;
  dashboardKey?: string;
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

export type DownloadedPlasticPdf = PlasticPdfSource & {
  path: string;
  sha256: string;
  bytes: number;
  fallback: boolean;
  error?: string;
};

export type ClientReadinessSeedManifest = {
  runId: string;
  actor: string;
  activeConfigVersion: number;
  records: {
    productRecordId: string;
    projectRecordIds: string[];
  };
  projects: Array<{ id: string; recordId: string; name: string }>;
  projectTasks: Array<{ id: number; projectId: string; title: string; state: string }>;
  workflowTasks: Array<{ id: number; title: string; state: string; relatedRecordId: string }>;
  managedFolders: Array<{ id: number; recordId: string; relativePath: string }>;
  folderEvents: Array<{ id: number; path: string; reviewStatus: string }>;
  dashboardKey: string;
};

export type QaUserSetup =
  | {
      ok: true;
      credentials: QaCredentials;
      engineer: QaCredentials;
      configAdmin: QaCredentials;
      systemAdmin: QaCredentials;
      readOnly: QaCredentials;
      fixtures: QaFixtures;
    }
  | { ok: false; message: string };

let cachedUserSetup: QaUserSetup | undefined;

export async function requireHealthyStack(request: APIRequestContext) {
  const health = await request.get("/api/health/", { timeout: 15_000 }).catch(() => null);
  if (!health?.ok()) {
    return { ok: false, message: `Local stack is unavailable at ${BASE_URL}` };
  }
  return { ok: true, message: "healthy" };
}

export function ensureQaUsers(): QaUserSetup {
  if (cachedUserSetup) {
    return cachedUserSetup;
  }

  if (process.env.ALLOW_E2E_USER_SEEDING === "true" && isLocalQaTarget(BASE_URL)) {
    cachedUserSetup = seedQaState();
    return cachedUserSetup;
  }

  const engineerUsername = process.env.E2E_USERNAME ?? process.env.E2E_ENGINEER_USERNAME;
  if (!engineerUsername || !process.env.E2E_PASSWORD) {
    cachedUserSetup = {
      ok: false,
      message:
        "QA credentials are not seeded. Set ALLOW_E2E_USER_SEEDING=true for a local stack or provide explicit role credentials."
    };
    return cachedUserSetup;
  }

  const provided = preprovisionedQaUsers();
  if (!provided) {
    cachedUserSetup = {
      ok: false,
      message:
        "When ALLOW_E2E_USER_SEEDING is false, provide E2E_USERNAME, E2E_CONFIG_ADMIN_USERNAME, E2E_SYSTEM_ADMIN_USERNAME, E2E_READONLY_USERNAME, and E2E_PASSWORD."
    };
    return cachedUserSetup;
  }

  cachedUserSetup = {
    ok: true,
    credentials: provided.engineer,
    engineer: provided.engineer,
    configAdmin: provided.configAdmin,
    systemAdmin: provided.systemAdmin,
    readOnly: provided.readOnly,
    fixtures: {}
  };
  return cachedUserSetup;
}

export async function loginWithSession(context: BrowserContext, credentials: QaCredentials) {
  const csrf = await getJson<{ csrfToken: string }>(context.request, "/api/accounts/csrf/");
  const response = await context.request.post("/api/accounts/login/", {
    headers: {
      "content-type": "application/json",
      "x-csrftoken": csrf.csrfToken
    },
    data: credentials
  });
  await expectJson(response, 200);
  const refreshedCsrf = await getJson<{ csrfToken: string }>(
    context.request,
    "/api/accounts/csrf/"
  );
  return { request: context.request, csrfToken: refreshedCsrf.csrfToken, credentials };
}

export async function createRecord(
  session: AuthenticatedSession,
  objectTypeKey: string,
  data: Record<string, unknown>,
  expectedStatus = 201
) {
  requireMutableQaTarget();
  return postJson<RecordPayload>(
    session,
    "/api/records/",
    {
      object_type_key: objectTypeKey,
      data
    },
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
  requireMutableQaTarget();
  const response = await session.request.post("/api/documents/", {
    headers: { "x-csrftoken": session.csrfToken },
    multipart: {
      owner_record: ownerRecordId,
      title,
      document_type: "technical_data_sheet",
      revision_label: revisionLabel,
      file: filePayload(filePath)
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
  requireMutableQaTarget();
  const response = await session.request.post(`/api/documents/${documentId}/revisions/`, {
    headers: { "x-csrftoken": session.csrfToken },
    multipart: {
      revision_label: revisionLabel,
      file: filePayload(filePath)
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

export async function downloadPlasticPdfSet(request: APIRequestContext) {
  const assetDir = path.join(REPO_ROOT, "frontend", "test-results", "qa-assets", "plastic-pdf-set");
  mkdirSync(assetDir, { recursive: true });
  const downloaded: DownloadedPlasticPdf[] = [];

  for (const [index, source] of plasticPdfManifest.entries()) {
    const pdfPath = path.join(assetDir, `${String(index + 1).padStart(2, "0")}-${safeAssetName(source.label)}.pdf`);
    const metaPath = `${pdfPath}.json`;
    let body: Buffer;
    let fallback = false;
    let error: string | undefined;

    if (existsSync(pdfPath) && existsSync(metaPath)) {
      const cached = JSON.parse(readFileSync(metaPath, "utf8")) as DownloadedPlasticPdf;
      downloaded.push(cached);
      continue;
    }

    try {
      const response = await request.get(source.url, { timeout: 45_000 });
      if (!response.ok()) {
        throw new Error(`HTTP ${response.status()} ${response.statusText()}`);
      }
      body = Buffer.from(await response.body());
      if (body.length <= 1_000 || body.subarray(0, 4).toString() !== "%PDF") {
        throw new Error(`Response was not a valid PDF fixture (${body.length} bytes).`);
      }
    } catch (caught) {
      fallback = true;
      error = caught instanceof Error ? caught.message : String(caught);
      body = fallbackPdfBytes(source);
    }

    expect(body.length, source.label).toBeGreaterThan(1_000);
    expect(body.subarray(0, 4).toString(), source.label).toBe("%PDF");
    writeFileSync(pdfPath, body);
    const sha256 = createHash("sha256").update(body).digest("hex");
    writeFileSync(`${pdfPath}.sha256`, sha256);
    const entry = {
      ...source,
      path: pdfPath,
      sha256,
      bytes: body.length,
      fallback,
      ...(error ? { error } : {})
    };
    writeFileSync(metaPath, JSON.stringify(entry, null, 2));
    downloaded.push(entry);
  }

  writeFileSync(path.join(assetDir, "manifest.json"), JSON.stringify(downloaded, null, 2));
  expect(downloaded).toHaveLength(20);
  return downloaded;
}

export async function getJson<T>(request: APIRequestContext, url: string, expectedStatus = 200) {
  const response = await request.get(url);
  await expectJson(response, expectedStatus);
  return response.json() as Promise<T>;
}

export async function postJson<T>(
  session: AuthenticatedSession,
  url: string,
  data: unknown,
  expectedStatus = 200
) {
  requireMutableQaTarget();
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
  requireMutableQaTarget();
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
  const body = await response.text();
  expect(response.status(), body).toBe(expectedStatus);
  const contentType = response.headers()["content-type"] ?? "";
  expect(contentType, body).toContain("application/json");
}

export function requireMutableQaTarget() {
  if (process.env.QA_ALLOW_NON_LOCAL_MUTATION === "true") {
    return;
  }
  if (isLocalQaTarget(BASE_URL)) {
    return;
  }
  throw new Error(
    `Refusing to mutate non-local QA target ${BASE_URL}. Set QA_ALLOW_NON_LOCAL_MUTATION=true to override.`
  );
}

export function seedClientReadinessDemo(runId: string) {
  requireMutableQaTarget();
  const output = execFileSync(
    "docker",
    [
      "compose",
      "-p",
      COMPOSE_PROJECT_NAME,
      "-f",
      "compose.yaml",
      "-f",
      "compose.dev.yaml",
      "exec",
      "-T",
      "-e",
      "ALLOW_CLIENT_READINESS_SEED=true",
      "backend",
      "python",
      "manage.py",
      "seed_client_readiness_demo",
      "--run-id",
      runId
    ],
    {
      cwd: REPO_ROOT,
      encoding: "utf-8",
      timeout: 120_000
    }
  );
  return JSON.parse(output.trim()) as ClientReadinessSeedManifest;
}

export function isLocalQaTarget(baseUrl: string) {
  try {
    const hostname = new URL(baseUrl).hostname.toLowerCase();
    return (
      ["localhost", "127.0.0.1", "::1", "[::1]", "plastic-hub.local", "backend"].includes(
        hostname
      ) ||
      hostname.endsWith(".local") ||
      hostname.startsWith("10.") ||
      hostname.startsWith("192.168.") ||
      /^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname)
    );
  } catch {
    return false;
  }
}

function seedQaState(): QaUserSetup {
  try {
    const output = execFileSync(
      "docker",
      [
        "compose",
        "-p",
        COMPOSE_PROJECT_NAME,
        "-f",
        "compose.yaml",
        "-f",
        "compose.dev.yaml",
        "exec",
        "-T",
        "backend",
        "python",
        "manage.py",
        "shell",
        "-c",
        seedScript()
      ],
      {
        cwd: REPO_ROOT,
        encoding: "utf-8",
        timeout: 60_000
      }
    );
    const parsed = JSON.parse(output.trim().split(/\r?\n/).at(-1) ?? "{}") as QaFixtures;
    return {
      ok: true,
      credentials: defaultEngineerCredentials(),
      engineer: defaultEngineerCredentials(),
      configAdmin: defaultConfigAdminCredentials(),
      systemAdmin: defaultSystemAdminCredentials(),
      readOnly: defaultReadOnlyCredentials(),
      fixtures: parsed
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      ok: false,
      message: `Unable to seed QA users/fixtures through docker compose: ${message}`
    };
  }
}

function defaultEngineerCredentials() {
  return {
    username: process.env.E2E_ENGINEER_USERNAME ?? "qa_engineer",
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

function preprovisionedQaUsers() {
  const password = process.env.E2E_PASSWORD;
  const engineer = process.env.E2E_USERNAME ?? process.env.E2E_ENGINEER_USERNAME;
  const configAdmin = process.env.E2E_CONFIG_ADMIN_USERNAME;
  const systemAdmin = process.env.E2E_SYSTEM_ADMIN_USERNAME;
  const readOnly = process.env.E2E_READONLY_USERNAME;

  if (!password || !engineer || !configAdmin || !systemAdmin || !readOnly) {
    return undefined;
  }

  return {
    engineer: { username: engineer, password },
    configAdmin: { username: configAdmin, password },
    systemAdmin: { username: systemAdmin, password },
    readOnly: { username: readOnly, password }
  };
}

function filePayload(filePath: string) {
  return {
    name: path.basename(filePath),
    mimeType: filePath.toLowerCase().endsWith(".pdf") ? "application/pdf" : "application/octet-stream",
    buffer: readFileSync(filePath)
  };
}

function safeAssetName(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function fallbackPdfBytes(source: PlasticPdfSource) {
  const escapedLabel = source.label.replace(/[()\\]/g, "");
  const escapedUrl = source.url.replace(/[()\\]/g, "");
  const body = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 220 >>
stream
BT /F1 12 Tf 72 720 Td (Client-readiness generated fallback plastics PDF.) Tj 0 -18 Td (${escapedLabel}) Tj 0 -18 Td (${escapedUrl}) Tj 0 -18 Td (Material data: density, tensile, impact, melt flow, compliance.) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
trailer
<< /Root 1 0 R >>
%%EOF
${"%".repeat(1200)}
`;
  return Buffer.from(body, "utf8");
}

function seedScript() {
  const password = JSON.stringify(process.env.E2E_PASSWORD ?? "qa-password-12345");
  return `
import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from apps.accounts.models import ObjectPermission
from apps.accounts.permissions import CONFIGURATION_ADMIN_ROLE, SYSTEM_ADMIN_ROLE
from apps.config_registry.models import ConfigurationVersion
from apps.config_registry.services import create_draft_from_current, publish_draft
from apps.projects.models import Project, ProjectBoardColumn, ProjectTask
from apps.projects.services import create_project
from apps.reports.models import Dashboard, DashboardWidget
from apps.workflows.models import WorkflowDefinition

password = ${password}
User = get_user_model()

def upsert_user(username, groups, is_superuser=False, is_staff=False):
    user, _ = User.objects.update_or_create(
        username=username,
        defaults={"is_active": True, "is_superuser": is_superuser, "is_staff": is_staff},
    )
    if not user.check_password(password):
        user.set_password(password)
        user.save(update_fields=["password"])
    group_objects = []
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        group_objects.append(group)
    user.groups.set(group_objects)
    return user

engineer = upsert_user("qa_engineer", ["Engineering"])
config_admin = upsert_user("qa_config_admin", [CONFIGURATION_ADMIN_ROLE, "Engineering"], is_staff=True)
system_admin = upsert_user("qa_system_admin", [SYSTEM_ADMIN_ROLE, "Engineering"], is_superuser=True, is_staff=True)
readonly = upsert_user("qa_readonly", ["Read Only"])

roles = {
    "Engineering": {"can_view": True, "can_create": True, "can_edit": True, "can_release": True, "can_admin": False},
    "Read Only": {"can_view": True, "can_create": False, "can_edit": False, "can_release": False, "can_admin": False},
    CONFIGURATION_ADMIN_ROLE: {"can_view": True, "can_create": True, "can_edit": True, "can_release": True, "can_admin": True},
    SYSTEM_ADMIN_ROLE: {"can_view": True, "can_create": True, "can_edit": True, "can_release": True, "can_admin": True},
}
for role, grants in roles.items():
    Group.objects.get_or_create(name=role)
    for object_type in ["product", "supplier", "raw_material", "product_spec", "project"]:
        ObjectPermission.objects.update_or_create(
            role_name=role,
            object_type_key=object_type,
            defaults=grants,
        )

if (
    not ConfigurationVersion.objects.exists()
    or not WorkflowDefinition.objects.filter(object_type_key="product_spec", is_active=True).exists()
):
    publish_draft(create_draft_from_current(system_admin), system_admin)

dashboard = Dashboard.objects.filter(config__key="quality_operations").first()
if dashboard is None:
    dashboard = Dashboard.objects.create(
        name="Quality Operations",
        description="QA seeded dashboard",
        config={"key": "quality_operations"},
    )
DashboardWidget.objects.get_or_create(
    dashboard=dashboard,
    title="QA Records by Status",
    defaults={"widget_type": "count_by_status", "config": {}, "sort_order": 1},
)

project = Project.objects.filter(name="QA Client Readiness Project").first()
if project is None:
    project = create_project(
        name="QA Client Readiness Project",
        actor=system_admin,
        description="Seeded for client-readiness QA",
        data={"project_type": "New Product"},
    )
todo, _ = ProjectBoardColumn.objects.get_or_create(
    project=project,
    key="todo",
    defaults={"title": "To Do", "sort_order": 1},
)
doing, _ = ProjectBoardColumn.objects.get_or_create(
    project=project,
    key="doing",
    defaults={"title": "Doing", "sort_order": 2},
)
first_task, _ = ProjectTask.objects.get_or_create(
    project=project,
    title="QA compound material",
    defaults={"column": todo, "estimated_hours": 2, "sort_order": 1, "assignee_user": engineer},
)
second_task, _ = ProjectTask.objects.get_or_create(
    project=project,
    title="QA run first molding pass",
    defaults={"column": todo, "estimated_hours": 3, "sort_order": 2, "assignee_user": engineer},
)

print(json.dumps({
    "projectId": str(project.pk),
    "projectRecordId": str(project.record_id),
    "todoColumnId": todo.pk,
    "doingColumnId": doing.pk,
    "firstTaskId": first_task.pk,
    "secondTaskId": second_task.pk,
    "dashboardKey": "quality_operations",
}))
`;
}

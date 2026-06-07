import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { APIRequestContext, APIResponse, BrowserContext, Page } from "@playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "https://plastic-hub.local";
const MEILI_URL = process.env.PLAYWRIGHT_MEILI_URL ?? "http://localhost:7700";
const MEILI_MASTER_KEY = process.env.MEILI_MASTER_KEY ?? "change-me";
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

// The current frontend has no login screen and the backend does not mount Django admin URLs.
// This e2e authenticates API traffic with DRF Basic auth instead of pretending a browser
// login workflow exists. Dev-only user seeding is refused unless ALLOW_E2E_USER_SEEDING=true
// and PLAYWRIGHT_BASE_URL points at a known local development host.
test.use({
  baseURL: BASE_URL,
  ignoreHTTPSErrors: true
});

test("traceability flow releases a controlled product spec and surfaces it in UI search and audit", async ({
  context,
  page,
  request
}) => {
  const health = await request.get("/api/health/", { timeout: 5_000 }).catch(() => null);
  test.skip(!health?.ok(), `Local stack is unavailable at ${BASE_URL}; start docker compose first.`);

  const meiliHealth = await meiliRequest("/health").catch(() => null);
  test.skip(
    meiliHealth?.status !== "available",
    `Meilisearch is unavailable at ${MEILI_URL}; set PLAYWRIGHT_MEILI_URL when it is not on localhost.`
  );

  const userSetup = ensureE2EUser();
  if (!userSetup.ok) {
    throw new Error(userSetup.message);
  }
  const credentials = userSetup.credentials;

  const auth = basicAuthHeader(credentials);
  await authorizeBrowserApiRequests(context, auth);

  const me = await getJson<{ username: string }>(request, "/api/accounts/me/", auth);
  expect(me.username).toBe(credentials.username);

  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "");
  const productName = `PW Traceable Film ${stamp}`;
  const specText = `Playwright traceability PDF text ${stamp} flame retardant polypropylene`;

  const supplier = await createRecord(request, auth, "supplier", {
    supplier_name: `PW North Polymer Supply ${stamp}`,
    supplier_code: `PW-NPS-${stamp}`,
    approved_status: "Approved"
  });
  const product = await createRecord(request, auth, "product", {
    commercial_name: productName,
    internal_grade: `PW-IF-${stamp}`,
    resin_family: "PP",
    application: "Medical packaging",
    color: "Natural"
  });

  expect(product.code).toMatch(/^PROD-\d{6}$/);

  const folder = await postJson<{ relative_path: string }>(
    request,
    `/api/records/${product.id}/folders/generate/`,
    {},
    auth
  );
  expect(folder.relative_path).toContain(product.code);

  const rawMaterial = await createRecord(request, auth, "raw_material", {
    supplier_material_code: `PW-RM-${stamp}`,
    material_family: "Base Resin",
    supplier: supplier.id,
    melt_flow_index: 12.5,
    density: 0.91,
    color: "Natural"
  });
  await postJson(
    request,
    "/api/relationships/",
    {
      source_record: product.id,
      target_record: rawMaterial.id,
      relationship_type_key: "product_uses_material",
      data: { basis: "primary resin" }
    },
    auth,
    201
  );

  const productSpec = await createRecord(request, auth, "product_spec", {
    spec_number: `PW-SPEC-${stamp}`,
    product: product.id,
    revision: "A",
    effective_date: "2026-06-07",
    release_notes: "Initial controlled release."
  });
  await postJson(
    request,
    "/api/relationships/",
    {
      source_record: product.id,
      target_record: productSpec.id,
      relationship_type_key: "product_has_spec",
      data: { revision: "A" }
    },
    auth,
    201
  );

  const document = await uploadSpecPdf(request, auth, productSpec.id, specText);
  const revision = document.current_revision;
  expect(revision.extraction_status).toBe("extracted");

  await page.goto(`/records/${productSpec.id}`);
  await expect(page.getByRole("heading", { name: productSpec.title })).toBeVisible();
  await expect(page.getByText("Controlled Product Spec")).toBeVisible();
  await expect(page.getByText("Extraction: extracted")).toBeVisible();
  await expect(page.getByText("Draft").first()).toBeVisible();

  await page.getByRole("button", { name: /Draft To Technical Review/i }).click();
  await completeTaskInUi(page, "Technical spec review");

  await page.goto(`/records/${productSpec.id}`);
  await page.getByRole("button", { name: /Technical Review To Approval/i }).click();
  await completeTaskInUi(page, "Approver signoff");

  await page.goto(`/records/${productSpec.id}`);
  await page.getByRole("button", { name: /Release revision A/i }).click();
  await expect(page.getByText("released").first()).toBeVisible();
  await page.getByRole("button", { name: /Approval To Released/i }).click();
  await expect(page.getByText("Released").first()).toBeVisible();

  await indexSearchDocuments(product, rawMaterial, productSpec, document, specText);

  await searchAndExpect(page, productName, productName);
  await searchAndExpect(page, "flame retardant polypropylene", "Controlled Product Spec");

  await page.goto("/audit");
  await expect(page.getByText("document.revision_released")).toBeVisible();
  await expect(page.getByText("workflow.transition_performed").first()).toBeVisible();
  await expect(page.getByText("relationship.created").first()).toBeVisible();
});

type RecordPayload = {
  id: string;
  object_type_key: string;
  code: string;
  title: string;
  status: string;
  data: Record<string, unknown>;
  updated_at: string;
};

type DocumentPayload = {
  id: number;
  title: string;
  state: string;
  current_revision: {
    id: number;
    revision_label: string;
    file_name: string;
    state: string;
    extraction_status: string;
    updated_at: string;
  };
  updated_at: string;
};

async function authorizeBrowserApiRequests(context: BrowserContext, authorization: string) {
  await context.route("**/api/**", async (route) => {
    await route.continue({
      headers: {
        ...route.request().headers(),
        authorization
      }
    });
  });
}

async function createRecord(
  request: APIRequestContext,
  authorization: string,
  objectTypeKey: string,
  data: Record<string, unknown>
) {
  return postJson<RecordPayload>(
    request,
    "/api/records/",
    {
      object_type_key: objectTypeKey,
      data
    },
    authorization,
    201
  );
}

async function completeTaskInUi(page: Page, title: string) {
  await page.goto("/tasks");
  const row = page.getByRole("row", { name: new RegExp(title, "i") });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: /Complete/i }).click();
  await expect(row).toHaveCount(0);
}

async function searchAndExpect(page: Page, query: string, expectedText: string) {
  await page.goto("/search");
  await page.getByLabel("Search query").fill(query);
  await page.getByRole("button", { name: /^Search$/i }).click();
  await expect(page.getByText(expectedText).first()).toBeVisible();
}

async function uploadSpecPdf(
  request: APIRequestContext,
  authorization: string,
  ownerRecordId: string,
  text: string
) {
  const response = await request.post("/api/documents/", {
    headers: { authorization },
    multipart: {
      owner_record: ownerRecordId,
      title: "Controlled Product Spec",
      document_type: "controlled_document",
      revision_label: "A",
      file: {
        name: "playwright-product-spec.pdf",
        mimeType: "application/pdf",
        buffer: pdfWithText(text)
      }
    }
  });
  return expectJson<DocumentPayload>(response, 201);
}

async function getJson<T>(
  request: APIRequestContext,
  url: string,
  authorization: string,
  expectedStatus = 200
) {
  const response = await request.get(url, { headers: { authorization } });
  return expectJson<T>(response, expectedStatus);
}

async function postJson<T>(
  request: APIRequestContext,
  url: string,
  data: unknown,
  authorization: string,
  expectedStatus = 200
) {
  const response = await request.post(url, {
    headers: {
      authorization,
      "content-type": "application/json"
    },
    data
  });
  return expectJson<T>(response, expectedStatus);
}

async function expectJson<T>(response: APIResponse, expectedStatus: number) {
  const body = await response.text();
  expect(response.status(), body).toBe(expectedStatus);
  return JSON.parse(body) as T;
}

type E2ECredentials = {
  username: string;
  password: string;
};

type E2EUserSetup =
  | { ok: true; credentials: E2ECredentials }
  | { ok: false; message: string; credentials?: never };

function ensureE2EUser(): E2EUserSetup {
  const explicitCredentials = credentialsFromEnvironment();
  if (!explicitCredentials) {
    return {
      ok: false,
      message:
        "Set E2E_USERNAME and E2E_PASSWORD for a pre-provisioned test account. " +
        "Dev-only seeding still requires both values and is available only with " +
        "ALLOW_E2E_USER_SEEDING=true against localhost, 127.0.0.1, ::1, or plastic-hub.local."
    };
  }

  if (allowDevUserSeeding()) {
    const seed = seedDevE2EUser(explicitCredentials);
    if (!seed.ok) {
      return { ok: false, message: seed.message };
    }
  }

  return { ok: true, credentials: explicitCredentials };
}

function credentialsFromEnvironment(): E2ECredentials | undefined {
  const username = process.env.E2E_USERNAME;
  const password = process.env.E2E_PASSWORD;

  if (username && password) {
    return { username, password };
  }

  if (username || password) {
    throw new Error("Both E2E_USERNAME and E2E_PASSWORD must be set together.");
  }

  return undefined;
}

function allowDevUserSeeding() {
  return process.env.ALLOW_E2E_USER_SEEDING === "true" && isLocalDevTarget(BASE_URL);
}

function isLocalDevTarget(baseUrl: string) {
  try {
    const hostname = new URL(baseUrl).hostname.toLowerCase();
    return ["localhost", "127.0.0.1", "::1", "[::1]", "plastic-hub.local"].includes(hostname);
  } catch {
    return false;
  }
}

function seedDevE2EUser(credentials: E2ECredentials) {
  const script = `
import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from apps.config_registry.models import ConfigurationVersion
from apps.config_registry.services import create_draft_from_current, publish_draft
from apps.workflows.models import WorkflowDefinition

username = ${JSON.stringify(credentials.username)}
password = ${JSON.stringify(credentials.password)}
User = get_user_model()
user, _ = User.objects.get_or_create(username=username)
user.is_active = True
user.is_staff = True
user.set_password(password)
user.save()
group, _ = Group.objects.get_or_create(name="System Admin")
user.groups.add(group)
if (
    not ConfigurationVersion.objects.exists()
    or not WorkflowDefinition.objects.filter(object_type_key="product_spec", is_active=True).exists()
):
    publish_draft(create_draft_from_current(user), user)
print(json.dumps({"username": username}))
`;

  try {
    execFileSync(
      "docker",
      [
        "compose",
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
        script
      ],
      {
        cwd: REPO_ROOT,
        encoding: "utf-8",
        timeout: 30_000
      }
    );
    return { ok: true };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      ok: false,
      message:
        "Dev-only backend setup failed. Run with the compose stack up, or use " +
        "E2E_USERNAME and E2E_PASSWORD for a pre-provisioned account. " +
        message
    };
  }
}

function basicAuthHeader(credentials: E2ECredentials) {
  return `Basic ${Buffer.from(`${credentials.username}:${credentials.password}`).toString("base64")}`;
}

function pdfWithText(text: string) {
  const escapedText = text.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
  const stream = `BT /F1 16 Tf 72 720 Td (${escapedText}) Tj ET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${Buffer.byteLength(stream, "ascii")} >>\nstream\n${stream}\nendstream`
  ];

  const offsets: number[] = [0];
  let pdf = "%PDF-1.4\n";
  objects.forEach((objectBody, index) => {
    offsets[index + 1] = Buffer.byteLength(pdf, "ascii");
    pdf += `${index + 1} 0 obj\n${objectBody}\nendobj\n`;
  });

  const xrefOffset = Buffer.byteLength(pdf, "ascii");
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  pdf += offsets
    .slice(1)
    .map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`)
    .join("");
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;

  return Buffer.from(pdf, "ascii");
}

async function indexSearchDocuments(
  product: RecordPayload,
  rawMaterial: RecordPayload,
  productSpec: RecordPayload,
  document: DocumentPayload,
  extractedText: string
) {
  await addDocuments("records", [
    {
      id: product.id,
      object_type_key: product.object_type_key,
      code: product.code,
      title: product.title,
      status: product.status,
      data_text: jsonValues(product.data).join(" "),
      relationship_text: [
        "product_uses_material",
        rawMaterial.code,
        rawMaterial.title,
        rawMaterial.object_type_key,
        "product_has_spec",
        productSpec.code,
        productSpec.title,
        productSpec.object_type_key
      ].join(" "),
      updated_at: product.updated_at
    }
  ]);
  await addDocuments("documents", [
    {
      id: String(document.current_revision.id),
      document_id: String(document.id),
      record_id: productSpec.id,
      title: document.title,
      revision: document.current_revision.revision_label,
      state: "released",
      filename: document.current_revision.file_name,
      extracted_text: extractedText,
      updated_at: document.current_revision.updated_at
    }
  ]);
}

async function addDocuments(indexName: string, documents: unknown[]) {
  const task = await meiliRequest(`/indexes/${indexName}/documents`, {
    method: "POST",
    body: JSON.stringify(documents)
  });
  await waitForMeiliTask(task.taskUid);
}

async function waitForMeiliTask(taskUid: number) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const task = await meiliRequest(`/tasks/${taskUid}`);
    if (task.status === "succeeded") {
      return;
    }
    if (task.status === "failed") {
      throw new Error(`Meilisearch task ${taskUid} failed: ${JSON.stringify(task)}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for Meilisearch task ${taskUid}.`);
}

async function meiliRequest(pathname: string, init: RequestInit = {}) {
  const response = await fetch(`${MEILI_URL}${pathname}`, {
    ...init,
    headers: {
      authorization: `Bearer ${MEILI_MASTER_KEY}`,
      "content-type": "application/json",
      ...init.headers
    }
  });
  if (!response.ok) {
    throw new Error(`Meilisearch request failed ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

function jsonValues(value: unknown): string[] {
  if (value === null || value === undefined) {
    return [];
  }
  if (Array.isArray(value)) {
    return value.flatMap(jsonValues);
  }
  if (typeof value === "object") {
    return Object.values(value).flatMap(jsonValues);
  }
  const text = String(value).trim();
  return text ? [text] : [];
}

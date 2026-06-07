import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { APIRequestContext, APIResponse, BrowserContext, Page } from "@playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "https://plastic-hub.local";
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

test.use({
  baseURL: BASE_URL,
  ignoreHTTPSErrors: true
});

test("traceability flow releases a controlled product spec and surfaces it in UI search and audit", async ({
  context,
  page,
  request
}) => {
  const health = await request.get("/api/health/", { timeout: 15_000 }).catch(() => null);
  test.skip(!health?.ok(), `Local stack is unavailable at ${BASE_URL}; start docker compose first.`);

  const userSetup = ensureE2EUser();
  if (!userSetup.ok) {
    throw new Error(userSetup.message);
  }
  const session = await loginWithSession(context, userSetup.credentials);

  const me = await getJson<{ username: string }>(session.request, "/api/accounts/me/");
  expect(me.username).toBe(userSetup.credentials.username);

  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "");
  const productName = `PW Traceable Film ${stamp}`;
  const specText = `Playwright traceability PDF text ${stamp} flame retardant polypropylene`;

  const supplier = await createRecord(session, "supplier", {
    supplier_name: `PW North Polymer Supply ${stamp}`,
    supplier_code: `PW-NPS-${stamp}`,
    approved_status: "Approved"
  });
  const product = await createRecord(session, "product", {
    commercial_name: productName,
    internal_grade: `PW-IF-${stamp}`,
    resin_family: "PP",
    application: "Medical packaging",
    color: "Natural"
  });

  expect(product.code).toMatch(/^PROD-\d{6}$/);

  const folder = await postJson<{ relative_path: string }>(
    session,
    `/api/records/${product.id}/folders/generate/`,
    {}
  );
  expect(folder.relative_path).toContain(product.code);

  const rawMaterial = await createRecord(session, "raw_material", {
    supplier_material_code: `PW-RM-${stamp}`,
    material_family: "Base Resin",
    supplier: supplier.id,
    melt_flow_index: 12.5,
    density: 0.91,
    color: "Natural"
  });
  await postJson(
    session,
    "/api/relationships/",
    {
      source_record: product.id,
      target_record: rawMaterial.id,
      relationship_type_key: "product_uses_material",
      data: { basis: "primary resin" }
    },
    201
  );

  const productSpec = await createRecord(session, "product_spec", {
    spec_number: `PW-SPEC-${stamp}`,
    product: product.id,
    revision: "A",
    effective_date: "2026-06-07",
    release_notes: "Initial controlled release."
  });
  await postJson(
    session,
    "/api/relationships/",
    {
      source_record: product.id,
      target_record: productSpec.id,
      relationship_type_key: "product_has_spec",
      data: { revision: "A" }
    },
    201
  );

  const document = await uploadSpecPdf(session, productSpec.id, specText);
  const revision = document.current_revision;
  expect(revision.extraction_status).toBe("extracted");

  await page.goto(`/records/${productSpec.id}`);
  await expect(page.getByRole("heading", { name: productSpec.title })).toBeVisible();
  await expect(page.getByText("Controlled Product Spec")).toBeVisible();
  await expect(page.getByText("Extraction: extracted")).toBeVisible();
  await expect(page.getByText("Draft").first()).toBeVisible();

  await clickTransitionAndWait(
    page,
    productSpec.id,
    "draft_to_technical_review",
    /Draft To Technical Review/i
  );
  await completeTaskInUi(page, "Technical spec review", productSpec.id);

  await page.goto(`/records/${productSpec.id}`);
  await clickTransitionAndWait(
    page,
    productSpec.id,
    "technical_review_to_approval",
    /Technical Review To Approval/i
  );
  await completeTaskInUi(page, "Approver signoff", productSpec.id);

  await page.goto(`/records/${productSpec.id}`);
  await page.getByRole("button", { name: /Release revision A/i }).click();
  await expect(page.getByText("released").first()).toBeVisible();
  await clickTransitionAndWait(
    page,
    productSpec.id,
    "approval_to_released",
    /Approval To Released/i
  );
  await expect(page.getByText("Released").first()).toBeVisible();

  await searchEventually(page, productName, productName);
  await searchEventually(page, "flame retardant polypropylene", "Controlled Product Spec");

  await page.goto("/audit");
  const auditEvents = page.getByRole("list", { name: /audit events/i }).getByRole("listitem");
  await expect(
    auditEvents
      .filter({ hasText: "document.revision_released" })
      .filter({ hasText: `document:${document.id}` })
  ).toBeVisible();
  await expect(
    auditEvents
      .filter({ hasText: "workflow.transition_performed" })
      .filter({ hasText: productSpec.id })
      .first()
  ).toBeVisible();
  await expect(
    auditEvents
      .filter({ hasText: "relationship.created" })
      .filter({ hasText: productSpec.id })
      .first()
  ).toBeVisible();
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

type AuthenticatedSession = {
  request: APIRequestContext;
  csrfToken: string;
};

async function loginWithSession(context: BrowserContext, credentials: E2ECredentials) {
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
  return { request: context.request, csrfToken: refreshedCsrf.csrfToken };
}

async function createRecord(
  session: AuthenticatedSession,
  objectTypeKey: string,
  data: Record<string, unknown>
) {
  return postJson<RecordPayload>(
    session,
    "/api/records/",
    {
      object_type_key: objectTypeKey,
      data
    },
    201
  );
}

async function clickTransitionAndWait(
  page: Page,
  recordId: string,
  transitionKey: string,
  buttonName: RegExp
) {
  const responsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      response.request().method() === "POST" &&
      response.ok() &&
      url.pathname === `/api/records/${recordId}/workflow/${transitionKey}/`
    );
  });

  await page.getByRole("button", { name: buttonName }).click();
  await responsePromise;
}

async function completeTaskInUi(page: Page, title: string, relatedRecordId: string) {
  await page.goto("/tasks");
  const row = page
    .getByRole("row")
    .filter({ hasText: new RegExp(escapeRegExp(title), "i") })
    .filter({ hasText: relatedRecordId });
  await expect(row).toBeVisible();
  const responsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      response.request().method() === "POST" &&
      response.ok() &&
      /^\/api\/workflow-tasks\/\d+\/complete\/$/.test(url.pathname)
    );
  });
  await row.getByRole("button", { name: /Complete/i }).click();
  await responsePromise;
  await expect(row).toHaveCount(0);
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function searchAndExpect(page: Page, query: string, expectedText: string) {
  await page.goto("/search");
  await page.getByLabel("Search query").fill(query);
  await page.getByRole("button", { name: /^Search$/i }).click();
  await expect(page.getByText(expectedText).first()).toBeVisible();
}

async function searchEventually(page: Page, query: string, expectedText: string) {
  await expect(async () => {
    await searchAndExpect(page, query, expectedText);
  }).toPass({
    intervals: [500, 1_000, 2_000],
    timeout: 30_000
  });
}

async function uploadSpecPdf(
  session: AuthenticatedSession,
  ownerRecordId: string,
  text: string
) {
  const response = await session.request.post("/api/documents/", {
    headers: { "x-csrftoken": session.csrfToken },
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
  expectedStatus = 200
) {
  const response = await request.get(url);
  return expectJson<T>(response, expectedStatus);
}

async function postJson<T>(
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

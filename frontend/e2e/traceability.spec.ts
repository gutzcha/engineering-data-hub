import { expect, test, type Page } from "@playwright/test";

import {
  BASE_URL,
  createRecord,
  ensureQaUsers,
  expectJson,
  getJson,
  loginWithSession,
  postJson,
  requireHealthyStack,
  type AuthenticatedSession
} from "./support/qaApi";

test.use({
  baseURL: BASE_URL,
  ignoreHTTPSErrors: true
});

test("traceability flow releases a controlled product spec and surfaces it in UI search and audit", async ({
  context,
  page,
  request
}) => {
  test.setTimeout(120_000);
  const health = await requireHealthyStack(request);
  test.skip(!health.ok, health.message);

  const users = ensureQaUsers();
  if (!users.ok) {
    throw new Error(users.message);
  }
  const session = await loginWithSession(context, users.systemAdmin);

  const me = await getJson<{ username: string }>(session.request, "/api/accounts/me/");
  expect(me.username).toBe(users.systemAdmin.username);

  const stamp = timestamp();
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
  await expect(page.getByRole("heading", { name: "Audit Timeline" })).toBeVisible();
  const documentAudit = await getJson<AuditPayload>(
    session.request,
    `/api/audit/?action=document.revision_released&object_type=document&object_id=${document.id}`
  );
  expect(documentAudit.results).toHaveLength(1);
  const workflowAudit = await getJson<AuditPayload>(
    session.request,
    "/api/audit/?action=workflow.transition_performed&limit=500"
  );
  expect(workflowAudit.results.some((event) => eventPayloadText(event).includes(productSpec.id))).toBe(
    true
  );
  const relationshipAudit = await getJson<AuditPayload>(
    session.request,
    "/api/audit/?action=relationship.created&object_type=relationship&limit=500"
  );
  expect(
    relationshipAudit.results.some(
      (event) =>
        eventPayloadText(event).includes(product.id) && eventPayloadText(event).includes(productSpec.id)
    )
  ).toBe(true);
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

type AuditPayload = {
  results: AuditEventPayload[];
};

type AuditEventPayload = {
  action: string;
  object_type: string;
  object_id: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
};

type WorkflowTaskPayload = {
  id: string | number;
  title?: string;
  name?: string;
  summary?: string;
  related_object_id?: string | number | null;
  related_record?: string | number | { id?: string | number } | null;
  record?: string | number | { id?: string | number } | null;
};

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
  const taskLoad = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      response.request().method() === "GET" &&
      response.ok() &&
      url.pathname === "/api/workflow-tasks/" &&
      url.searchParams.get("state") === "open"
    );
  });
  await page.goto("/tasks");
  const tasks = (await (await taskLoad).json()) as WorkflowTaskPayload[];
  const task = tasks.find(
    (candidate) =>
      taskPayloadTitle(candidate).toLowerCase() === title.toLowerCase() &&
      String(taskPayloadRelatedId(candidate)) === relatedRecordId
  );
  if (!task) {
    throw new Error(`Expected open workflow task "${title}" for record ${relatedRecordId}.`);
  }

  await page.getByLabel(/search tasks/i).fill(title);
  const row = page
    .getByRole("row")
    .filter({ hasText: new RegExp(escapeRegExp(title), "i") })
    .filter({ hasText: `#${relatedRecordId}` });
  await expect(row).toBeVisible();
  const responsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      response.request().method() === "POST" &&
      response.ok() &&
      url.pathname === `/api/workflow-tasks/${task.id}/complete/`
    );
  });
  const taskReload = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      response.request().method() === "GET" &&
      response.ok() &&
      url.pathname === "/api/workflow-tasks/" &&
      url.searchParams.get("state") === "open"
    );
  });
  await row.getByRole("button", { name: /Complete/i }).click();
  await responsePromise;
  await taskReload;
  await expect(row).toHaveCount(0, { timeout: 30_000 });
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function taskPayloadTitle(task: WorkflowTaskPayload) {
  return task.title ?? task.name ?? task.summary ?? `Task ${task.id}`;
}

function taskPayloadRelatedId(task: WorkflowTaskPayload) {
  return task.related_object_id ?? relationId(task.related_record) ?? relationId(task.record);
}

function relationId(relation?: string | number | { id?: string | number } | null) {
  if (relation === undefined || relation === null || relation === "") {
    return undefined;
  }

  return typeof relation === "object" ? relation.id : relation;
}

function eventPayloadText(event: AuditEventPayload) {
  return JSON.stringify({
    object_id: event.object_id,
    before: event.before,
    after: event.after
  });
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
  await expectJson(response, 201);
  return response.json() as Promise<DocumentPayload>;
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

function timestamp() {
  const time = new Date().toISOString().replace(/[-:.TZ]/g, "");
  return `${time}-${Math.random().toString(36).slice(2, 8)}`;
}

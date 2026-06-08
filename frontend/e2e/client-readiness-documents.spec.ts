import { expect, test, type APIResponse } from "@playwright/test";

import {
  addDocumentRevision,
  createRecord,
  downloadExternalPdf,
  ensureQaUsers,
  getJson,
  loginWithSession,
  requireHealthyStack,
  uploadDocumentRevision,
  type AuthenticatedSession,
  type DocumentPayload
} from "./support/qaApi";
import { readinessGate } from "./support/strictReadiness";

type DocumentPreviewPayload = {
  extraction_status: string;
  extracted_text: string;
};

test.describe("client readiness document lifecycle", () => {
  test.beforeEach(async ({ request }) => {
    const health = await requireHealthyStack(request);
    readinessGate(!health.ok, health.message);

    const users = ensureQaUsers();
    readinessGate(!users.ok, users.message);
  });

  test("real polycarbonate PDF uploads, previews, downloads, releases, and protects released revisions", async ({
    context,
    page,
    request
  }) => {
    const users = ensureQaUsers();
    if (!users.ok) {
      throw new Error(users.message);
    }

    const session = await loginWithSession(context, users.engineer);
    const stamp = timestamp();
    const pdfPath = await downloadExternalPdf(request);

    const product = await createRecord(session, "product", {
      commercial_name: `QA Polycarbonate Document ${stamp}`,
      internal_grade: `QA-DOC-PC-${stamp}`,
      resin_family: "PC",
      application: "Transparent machine guard",
      color: "Clear"
    });

    const document = await uploadDocumentRevision(
      session,
      product.id,
      `QA Plastic-Craft Polycarbonate TDS ${stamp}`,
      "A",
      pdfPath
    );
    const revisionA = document.current_revision;
    expect(revisionA, "initial revision A is created").not.toBeNull();
    expect(revisionA?.revision_label).toBe("A");
    expect(revisionA?.extraction_status).toBe("extracted");

    await page.goto(`/records/${product.id}`);
    await expect(page.getByRole("heading", { name: product.title })).toBeVisible();
    await expect(page.getByText(document.title)).toBeVisible();
    await expect(page.getByText(/Extraction:\s*extracted/i)).toBeVisible();

    const preview = await getJson<DocumentPreviewPayload>(
      session.request,
      `/api/documents/${document.id}/preview/`
    );
    expect(preview.extraction_status).toBe("extracted");
    expect(preview.extracted_text).toMatch(/polycarbonate/i);
    expect(materialPropertyTermCount(preview.extracted_text)).toBeGreaterThanOrEqual(2);

    const download = await session.request.get(`/api/documents/${document.id}/download/`);
    expect(download.status()).toBe(200);
    expect(download.headers()["content-type"]).toContain("application/pdf");
    const downloadedBytes = await download.body();
    expect(downloadedBytes.length).toBeGreaterThan(1_000);
    expect(downloadedBytes.subarray(0, 4).toString()).toBe("%PDF");

    const release = await session.request.post(
      `/api/documents/${document.id}/revisions/${revisionA?.id}/release/`,
      { headers: { "x-csrftoken": session.csrfToken } }
    );
    const releasedRevision = await expectStatusJson<NonNullable<DocumentPayload["current_revision"]>>(
      release,
      200
    );
    expect(releasedRevision.revision_label).toBe("A");
    expect(releasedRevision.state).toBe("released");

    const revisionB = await addDocumentRevision(session, document.id, "B", pdfPath, 201);
    const revisionBPayload = await revisionB.json();
    expect(revisionBPayload.revision_label).toBe("B");
    expect(revisionBPayload.extraction_status).toBe("extracted");

    const replaceReleasedA = await addDocumentRevision(session, document.id, "A", pdfPath, 400);
    const replaceBody = await replaceReleasedA.json();
    expect(replaceBody.revision_label?.join(" ")).toMatch(/released revisions cannot be replaced/i);

    await expectDocumentMethodUnavailable(session, document.id, "patch");
    await expectDocumentMethodUnavailable(session, document.id, "delete");
  });

  test("document library lists and retrieves controlled document metadata", async ({
    context,
    page,
    request
  }) => {
    test.setTimeout(120_000);
    const users = ensureQaUsers();
    if (!users.ok) {
      throw new Error(users.message);
    }

    const session = await loginWithSession(context, users.engineer);
    const stamp = timestamp();
    const pdfPath = await downloadExternalPdf(request);
    const product = await createRecord(session, "product", {
      commercial_name: `QA Document Library Gap ${stamp}`,
      internal_grade: `QA-DOC-LIB-${stamp}`,
      resin_family: "PC",
      application: "Library readiness probe",
      color: "Clear"
    });
    const document = await uploadDocumentRevision(
      session,
      product.id,
      `QA Document Library ${stamp}`,
      "A",
      pdfPath
    );

    const listResponse = await session.request.get("/api/documents/");
    const listBody = await expectStatusJson<DocumentPayload[]>(listResponse, 200);
    expect(listBody.some((item) => item.id === document.id)).toBe(true);

    const retrieveResponse = await session.request.get(`/api/documents/${document.id}/`);
    const retrieveBody = await expectStatusJson<DocumentPayload>(retrieveResponse, 200);
    expect(retrieveBody.title).toBe(document.title);
    expect(retrieveBody.current_revision?.extraction_status).toBe("extracted");

    await page.goto("/documents");
    await expect(page.getByRole("heading", { level: 1, name: "Documents" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Document Library/i })).toBeVisible();
    await expect(page.getByRole("link", { name: document.title }).first()).toBeVisible();

    await page.goto(`/documents/${document.id}`);
    await expect(page.getByRole("heading", { name: document.title })).toBeVisible();
    await expect(page.getByText(/Extraction:\s*extracted/i)).toBeVisible();
  });
});

async function expectDocumentMethodUnavailable(
  session: AuthenticatedSession,
  documentId: number,
  method: "patch" | "delete"
) {
  const response =
    method === "patch"
      ? await session.request.patch(`/api/documents/${documentId}/`, {
          headers: {
            "content-type": "application/json",
            "x-csrftoken": session.csrfToken
          },
          data: { title: "QA blocked document patch" }
        })
      : await session.request.delete(`/api/documents/${documentId}/`, {
          headers: { "x-csrftoken": session.csrfToken }
        });
  expect([404, 405]).toContain(response.status());
}

async function expectStatusJson<T>(response: APIResponse, expectedStatus: number) {
  const body = await response.text();
  const bodySummary = summarizeResponseBody(body);
  expect(response.status(), bodySummary).toBe(expectedStatus);
  expect(response.headers()["content-type"] ?? "", bodySummary).toContain("application/json");
  return JSON.parse(body) as T;
}

function summarizeResponseBody(body: string) {
  const title = body.match(/<title>([\s\S]*?)<\/title>/i)?.[1]?.replace(/\s+/g, " ").trim();
  const exception = body
    .match(/<pre class="exception_value">([\s\S]*?)<\/pre>/i)?.[1]
    ?.replace(/\s+/g, " ")
    .trim();
  const htmlSummary = [title, exception].filter(Boolean).join(" - ");

  return htmlSummary || body.slice(0, 1_000);
}

function materialPropertyTermCount(text: string) {
  const normalized = text.toLowerCase();
  const terms = [
    /density/,
    /specific\s+gravity/,
    /tensile/,
    /flexural/,
    /modulus/,
    /heat\s+deflection/,
    /flammability/,
    /impact/
  ];

  return terms.filter((term) => term.test(normalized)).length;
}

function timestamp() {
  const time = new Date().toISOString().replace(/[-:.TZ]/g, "");
  return `${time}-${Math.random().toString(36).slice(2, 8)}`;
}

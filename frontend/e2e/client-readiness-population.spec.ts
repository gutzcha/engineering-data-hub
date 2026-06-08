import { expect, test } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

import {
  createRecord,
  downloadPlasticPdfSet,
  ensureQaUsers,
  getJson,
  loginWithSession,
  requireHealthyStack,
  REPO_ROOT,
  seedClientReadinessDemo,
  uploadDocumentRevision,
  type DocumentPayload,
  type RecordPayload
} from "./support/qaApi";
import { readinessGate } from "./support/strictReadiness";

test.describe("client readiness full data population", () => {
  test.beforeEach(async ({ request }) => {
    readinessGate(
      process.env.QA_POPULATE_FULL_DATASET !== "true",
      "Set QA_POPULATE_FULL_DATASET=true to run the full client-readiness population pass."
    );
    const health = await requireHealthyStack(request);
    readinessGate(!health.ok, health.message);
    const users = ensureQaUsers();
    readinessGate(!users.ok, users.ok ? "" : users.message);
  });

  test("downloads 20 plastic PDFs, seeds operational objects, and uploads controlled documents", async ({
    context,
    page,
    request
  }) => {
    test.setTimeout(180_000);
    const users = ensureQaUsers();
    if (!users.ok) {
      throw new Error(users.message);
    }

    const runId = `qa-client-readiness-${timestamp()}`;
    const seedManifest = seedClientReadinessDemo(runId);
    expect(seedManifest.projects).toHaveLength(4);
    expect(seedManifest.projectTasks).toHaveLength(16);
    expect(seedManifest.workflowTasks.length).toBeGreaterThanOrEqual(4);
    expect(seedManifest.folderEvents).toHaveLength(6);

    const session = await loginWithSession(context, users.engineer);
    const pdfs = await downloadPlasticPdfSet(request);
    expect(pdfs).toHaveLength(20);

    const suppliers: RecordPayload[] = [];
    for (let index = 0; index < 10; index += 1) {
      suppliers.push(
        await createRecord(session, "supplier", {
          supplier_name: `${supplierNames[index]} ${runId}`,
          supplier_code: `SUP-${index + 1}-${runId}`,
          contact_email: `qa-supplier-${index + 1}@example.test`,
          approved_status: index % 3 === 0 ? "Conditional" : "Approved"
        })
      );
    }

    const rawMaterials: RecordPayload[] = [];
    for (let index = 0; index < 20; index += 1) {
      rawMaterials.push(
        await createRecord(session, "raw_material", {
          supplier_material_code: `${materialCodes[index]}-${runId}`,
          material_family: materialFamilies[index % materialFamilies.length],
          supplier: suppliers[index % suppliers.length].id,
          melt_flow_index: Number((4 + index * 0.7).toFixed(1)),
          density: Number((0.9 + index * 0.015).toFixed(3)),
          color: materialColors[index % materialColors.length]
        })
      );
    }

    const products: RecordPayload[] = [];
    for (let index = 0; index < 15; index += 1) {
      products.push(
        await createRecord(session, "product", {
          commercial_name: `${productNames[index]} ${runId}`,
          internal_grade: `QA-GRADE-${index + 1}-${runId}`,
          resin_family: productResinFamilies[index % productResinFamilies.length],
          application: productApplications[index % productApplications.length],
          color: materialColors[index % materialColors.length],
          regulatory_notes: "QA populated record for client-readiness review.",
          status_notes: "Generated through Playwright population pass."
        })
      );
    }

    const productSpecs: RecordPayload[] = [];
    for (let index = 0; index < 12; index += 1) {
      productSpecs.push(
        await createRecord(session, "product_spec", {
          spec_number: `SPEC-${index + 1}-${runId}`,
          product: products[index % products.length].id,
          revision: "A",
          effective_date: "2026-06-08",
          release_notes: "QA specification populated for end-to-end validation."
        })
      );
    }

    const ownerRecords = [...products, ...rawMaterials, ...productSpecs];
    const documents: DocumentPayload[] = [];
    for (const [index, pdf] of pdfs.entries()) {
      const owner = ownerRecords[index % ownerRecords.length];
      documents.push(
        await uploadDocumentRevision(
          session,
          owner.id,
          `${pdf.label} ${runId}`,
          "A",
          pdf.path
        )
      );
    }

    const documentList = await getJson<DocumentPayload[]>(session.request, "/api/documents/");
    for (const document of documents) {
      expect(documentList.some((item) => item.id === document.id)).toBe(true);
      expect(document.current_revision, document.title).not.toBeNull();
    }

    await page.goto("/documents");
    await expect(page.getByRole("heading", { level: 1, name: "Documents" })).toBeVisible();
    await expect(page.getByRole("link", { name: documents[0].title }).first()).toBeVisible();

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Operational Overview" })).toBeVisible();
    await expect(page.getByRole("link", { name: /controlled documents/i })).toBeVisible();

    writePopulationReport({
      runId,
      seedManifest,
      pdfs,
      suppliers,
      rawMaterials,
      products,
      productSpecs,
      documents
    });
  });
});

const supplierNames = [
  "Northline Resin Distribution",
  "MoldTek Compounding",
  "ClearSheet Plastics",
  "BondFast Adhesives",
  "ColorPlus Masterbatch",
  "Circular Resin Recovery",
  "Metro Polymer Lab",
  "Precision Mold Works",
  "PackRight Components",
  "Regulatory Polymer Services"
];

const materialCodes = [
  "PC-CLEAR",
  "ABS-HI",
  "HDPE-NAT",
  "LDPE-FLEX",
  "PP-HOMO",
  "PA66-GF",
  "POM-NAT",
  "PVC-RIGID",
  "PMMA-OPT",
  "HIPS-WHT",
  "PETG-CLR",
  "TPU-85A",
  "TPE-BLK",
  "NYLON-GF30",
  "PC-REGRIND",
  "R-HDPE",
  "PP-UV",
  "PCABS-FR",
  "PVC-CEMENT",
  "COLOR-MB"
];

const materialFamilies = ["Base Resin", "Additive", "Colorant", "Masterbatch", "Filler"];
const materialColors = ["Clear", "Natural", "Black", "White", "Blue", "Gray"];
const productResinFamilies = ["PP", "PE", "HDPE", "LDPE", "LLDPE"];
const productNames = [
  "Molded Control Enclosure",
  "Transparent Machine Guard",
  "Cable Retention Clip",
  "Fluid Routing Manifold",
  "Laboratory Tray",
  "Appliance Selector Knob",
  "Outdoor Mounting Bracket",
  "Packaging Insert",
  "Medical Device Housing",
  "Conveyor Guide",
  "Lens Protection Cover",
  "Welding Fixture",
  "Battery Cell Spacer",
  "Valve Body",
  "Recycled Content Panel"
];
const productApplications = [
  "Injection molded enclosure",
  "Transparent safety guarding",
  "Wire harness retention",
  "Fluid handling",
  "Laboratory handling",
  "Consumer appliance control"
];

function writePopulationReport(data: {
  runId: string;
  seedManifest: unknown;
  pdfs: Array<{ label: string; url: string; path: string; sha256: string; fallback: boolean; bytes: number }>;
  suppliers: RecordPayload[];
  rawMaterials: RecordPayload[];
  products: RecordPayload[];
  productSpecs: RecordPayload[];
  documents: DocumentPayload[];
}) {
  const reportPath = path.join(REPO_ROOT, "docs", "qa", "findings", "population-run.md");
  mkdirSync(path.dirname(reportPath), { recursive: true });
  const pdfRows = data.pdfs
    .map(
      (pdf, index) =>
        `| ${index + 1} | ${pdf.label} | ${pdf.fallback ? "generated fallback" : "downloaded"} | ${pdf.bytes} | \`${pdf.sha256}\` | ${pdf.url} |`
    )
    .join("\n");
  const documentRows = data.documents
    .map(
      (document, index) =>
        `| ${index + 1} | ${document.id} | ${document.title} | ${document.current_revision?.extraction_status ?? "unknown"} |`
    )
    .join("\n");

  writeFileSync(
    reportPath,
    `# Client Readiness Population Run

Run ID: ${data.runId}

## Counts

- Suppliers: ${data.suppliers.length}
- Raw materials: ${data.rawMaterials.length}
- Products: ${data.products.length}
- Product specs: ${data.productSpecs.length}
- Controlled documents: ${data.documents.length}

## Seed Manifest

\`\`\`json
${JSON.stringify(data.seedManifest, null, 2)}
\`\`\`

## PDF Sources

| # | Label | Source status | Bytes | SHA-256 | URL |
|---|---|---|---:|---|---|
${pdfRows}

## Uploaded Documents

| # | Document ID | Title | Extraction |
|---|---|---|---|
${documentRows}
`,
    "utf8"
  );
}

function timestamp() {
  return `${new Date().toISOString().replace(/[-:.TZ]/g, "")}-${Math.random().toString(36).slice(2, 8)}`;
}

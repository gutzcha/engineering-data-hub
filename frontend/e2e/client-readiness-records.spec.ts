import { expect, test, type APIResponse, type Response as PageResponse } from "@playwright/test";

import {
  createRecord,
  ensureQaUsers,
  expectJson,
  getJson,
  loginWithSession,
  patchJson,
  postJson,
  requireHealthyStack,
  requireMutableQaTarget,
  type RecordPayload
} from "./support/qaApi";
import { ensureQaReport, recordFinding } from "./support/qaReport";

type FieldDefinition = {
  key: string;
  label?: string;
  required?: boolean;
};

type ObjectTypeDefinition = {
  key: string;
  label?: string;
  plural_label?: string;
  fields?: FieldDefinition[];
};

type ConfigData = {
  object_types?: ObjectTypeDefinition[];
};

type ConfigVersion = {
  id: number;
  version: number;
  data: ConfigData;
};

type ConfigDraft = {
  id: number;
  status: string;
  data: ConfigData;
};

type ValidationIssue = {
  path: string;
  code: string;
  message: string;
};

type ValidationResult = {
  errors: ValidationIssue[];
  breaking_changes?: ValidationIssue[];
};

test.describe("client readiness records and admin controls", () => {
  test.beforeEach(async ({ request }) => {
    const health = await requireHealthyStack(request);
    test.skip(!health.ok, health.message);

    const users = ensureQaUsers();
    if (!users.ok) {
      test.skip(true, users.message);
    }
    ensureQaReport();
  });

  test("UI New Record flow creates a product using the published field labels", async ({
    context,
    page
  }) => {
    requireMutableQaTarget();
    const users = requireQaUsers();
    const session = await loginWithSession(context, users.engineer);
    const activeConfig = await getJson<ConfigVersion>(session.request, "/api/config/active/");
    const productType = objectType(activeConfig.data, "product");
    const stamp = timestamp();
    const productName = `QA Polycarbonate Label Flow ${stamp}`;

    await page.goto("/records");
    await expect(page.getByRole("heading", { name: "Records" })).toBeVisible();
    await page.getByRole("link", { name: /new record/i }).click();
    await expect(page).toHaveURL(/\/records\/new/);
    await expect(page.getByRole("heading", { name: /new record/i })).toBeVisible();

    await page
      .getByLabel("Object type", { exact: true })
      .selectOption({ label: objectTypeLabel(productType) });
    await page
      .getByLabel(fieldLabel(productType, "commercial_name"), { exact: true })
      .fill(productName);
    await page
      .getByLabel(fieldLabel(productType, "internal_grade"), { exact: true })
      .fill(`QA-PC-LABEL-${stamp}`);
    await page
      .getByLabel(fieldLabel(productType, "resin_family"), { exact: true })
      .selectOption("PC");
    await page
      .getByLabel(fieldLabel(productType, "application"), { exact: true })
      .fill("Transparent diagnostic instrument housing");
    await page
      .getByLabel(fieldLabel(productType, "color"), { exact: true })
      .fill("Clear");

    const createResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === "/api/records/"
    );
    await page.getByRole("button", { name: /create record/i }).click();
    const created = await expectPageJsonResponse<RecordPayload>(await createResponse, 201);

    await expect(page).toHaveURL(new RegExp(`/records/${created.id}$`));
    await expect(page.getByRole("heading", { name: productName })).toBeVisible();
    await expect(page.getByText(created.code)).toBeVisible();
    await expect(page.getByRole("button", { name: /delete/i })).toHaveCount(0);
    await expect(page.getByRole("link", { name: /delete/i })).toHaveCount(0);
  });

  test("API records can be created, edited, released, and not deleted", async ({ context }) => {
    requireMutableQaTarget();
    const users = requireQaUsers();
    const session = await loginWithSession(context, users.engineer);
    const stamp = timestamp();

    const product = await createRecord(session, "product", {
      commercial_name: `QA API Housing ${stamp}`,
      internal_grade: `QA-PC-API-${stamp}`,
      resin_family: "PC",
      application: "Handheld meter enclosure",
      color: "Black"
    });
    expect(product.status).toBe("draft");

    const patched = await patchJson<RecordPayload>(session, `/api/records/${product.id}/`, {
      data: {
        color: "Transparent black",
        status_notes: "QA edit through client-readiness API gate"
      }
    });
    expect(patched.data.color).toBe("Transparent black");
    expect(patched.data.status_notes).toBe("QA edit through client-readiness API gate");

    const deleteResponse = await session.request.delete(`/api/records/${product.id}/`, {
      headers: { "x-csrftoken": session.csrfToken }
    });
    const deleteBody = await deleteResponse.text();
    expect([403, 405], deleteBody).toContain(deleteResponse.status());
    expect(deleteResponse.headers()["content-type"] ?? "", deleteBody).toContain(
      "application/json"
    );

    const releaseResponse = await session.request.post(`/api/records/${product.id}/release/`, {
      headers: { "x-csrftoken": session.csrfToken }
    });
    const released = await expectJsonResponse<RecordPayload>(releaseResponse, 200);
    expect(released.status).toBe("released");
  });

  test("archive and record-version endpoints are required client-readiness gates", async ({
    context
  }, testInfo) => {
    requireMutableQaTarget();
    const users = requireQaUsers();
    const session = await loginWithSession(context, users.systemAdmin);
    const stamp = timestamp();
    const product = await createRecord(session, "product", {
      commercial_name: `QA Archive Version Gate ${stamp}`,
      internal_grade: `QA-ARCH-${stamp}`,
      resin_family: "PP",
      application: "Tamper-evident closure",
      color: "Natural"
    });

    const archiveResponse = await session.request.post(`/api/records/${product.id}/archive/`, {
      headers: { "x-csrftoken": session.csrfToken }
    });
    if ([404, 405].includes(archiveResponse.status())) {
      recordFinding(
        {
          id: "QA-GAP-001",
          severity: "Critical",
          area: "Records",
          title: "Records cannot be archived",
          expected: "Authorized users can archive a record instead of deleting it.",
          actual: `Archive endpoint returned ${archiveResponse.status()}.`,
          evidence: `/api/records/${product.id}/archive/`
        },
        testInfo
      );
    }
    await expectEndpointAvailable(archiveResponse, "archive endpoint must exist");

    const versionResponse = await session.request.post(`/api/records/${product.id}/versions/`, {
      headers: {
        "content-type": "application/json",
        "x-csrftoken": session.csrfToken
      },
      data: { change_note: "QA version gate" }
    });
    if ([404, 405].includes(versionResponse.status())) {
      recordFinding(
        {
          id: "QA-GAP-002",
          severity: "Critical",
          area: "Records",
          title: "Records cannot create or browse versions",
          expected: "Authorized users can create a new record version and inspect prior versions.",
          actual: `Record version endpoint returned ${versionResponse.status()}.`,
          evidence: `/api/records/${product.id}/versions/`
        },
        testInfo
      );
    }
    await expectEndpointAvailable(versionResponse, "record version endpoint must exist");
  });

  test("normal users cannot access or mutate configuration drafts", async ({ context }) => {
    requireMutableQaTarget();
    const users = requireQaUsers();
    const session = await loginWithSession(context, users.engineer);

    const history = await session.request.get("/api/config/history/");
    expect(history.status(), await history.text()).toBe(403);

    const createDraft = await session.request.post("/api/config/drafts/", {
      headers: { "x-csrftoken": session.csrfToken }
    });
    expect(createDraft.status(), await createDraft.text()).toBe(403);

    const updateDraft = await session.request.patch("/api/config/drafts/1/", {
      headers: {
        "content-type": "application/json",
        "x-csrftoken": session.csrfToken
      },
      data: { data: { object_types: [] } }
    });
    expect(updateDraft.status(), await updateDraft.text()).toBe(403);

    const validateDraft = await session.request.post("/api/config/drafts/1/validate/", {
      headers: { "x-csrftoken": session.csrfToken }
    });
    expect(validateDraft.status(), await validateDraft.text()).toBe(403);

    const publishDraft = await session.request.post("/api/config/drafts/1/publish/", {
      headers: { "x-csrftoken": session.csrfToken }
    });
    expect(publishDraft.status(), await publishDraft.text()).toBe(403);
  });

  test("configuration admin cannot publish destructive field removals", async ({
    context
  }, testInfo) => {
    requireMutableQaTarget();
    const users = requireQaUsers();
    const session = await loginWithSession(context, users.configAdmin);
    const activeConfig = await getJson<ConfigVersion>(session.request, "/api/config/active/");
    const destructiveDraftData = configWithProductFieldRemoved(activeConfig.data);

    const draft = await postJson<ConfigDraft>(session, "/api/config/drafts/", {}, 201);
    await patchJson<ConfigDraft>(session, `/api/config/drafts/${draft.id}/`, {
      data: destructiveDraftData.data
    });
    const validation = await postJson<ValidationResult>(
      session,
      `/api/config/drafts/${draft.id}/validate/`,
      {}
    );
    expect(validation.errors).toEqual([]);
    expect(validation.breaking_changes ?? []).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          code: "field_removed",
          path: `object_types.product.fields.${destructiveDraftData.removedFieldKey}`
        })
      ])
    );

    const publishResponse = await session.request.post(
      `/api/config/drafts/${draft.id}/publish/`,
      {
        headers: { "x-csrftoken": session.csrfToken },
        data: {}
      }
    );
    const publishBody = await publishResponse.text();
    if (publishResponse.status() !== 403) {
      recordFinding(
        {
          id: "QA-ADMIN-001",
          severity: "Critical",
          area: "Admin Configuration",
          title: "Configuration admin can reach destructive publish path",
          expected: "Destructive configuration changes require System Admin approval.",
          actual: `Publish returned ${publishResponse.status()} instead of 403.`,
          evidence: `/api/config/drafts/${draft.id}/publish/`
        },
        testInfo
      );
    }
    expect(publishResponse.status(), publishBody).toBe(403);
    expect(publishBody).toMatch(/Destructive configuration changes require System Admin approval/i);
  });

  test("React admin navigation works and direct /admin reload does not fall through to Django admin", async ({
    context,
    page
  }, testInfo) => {
    const users = requireQaUsers();
    await loginWithSession(context, users.configAdmin);

    await page.goto("/");
    await page
      .getByRole("navigation", { name: /primary navigation/i })
      .getByRole("link", { name: "Admin" })
      .click();
    await expect(page.getByRole("heading", { name: /admin configuration/i })).toBeVisible();

    const reloadResponse = await page.goto("/admin");
    await page.waitForLoadState("domcontentloaded");
    const bodyText = await page.locator("body").innerText();
    const reactHeadingCount = await page
      .getByRole("heading", { name: /admin configuration/i })
      .count();
    const fellThroughToDjango = /Django administration/i.test(bodyText);

    if (reactHeadingCount === 0 || fellThroughToDjango) {
      recordFinding(
        {
          id: "QA-ROUTE-001",
          severity: "High",
          area: "Routing",
          title: "Direct /admin reload does not serve the React admin workspace",
          expected: "Direct reload of /admin serves the React Admin Configuration route.",
          actual: fellThroughToDjango
            ? "The page body contains Django administration."
            : "The React Admin Configuration heading was not rendered.",
          evidence: `GET /admin returned ${reloadResponse?.status() ?? "unknown"} at ${page.url()}`
        },
        testInfo
      );
    }

    expect(fellThroughToDjango, bodyText).toBe(false);
    expect(reactHeadingCount, bodyText).toBeGreaterThan(0);
  });
});

function requireQaUsers() {
  const users = ensureQaUsers();
  if (!users.ok) {
    throw new Error(users.message);
  }
  return users;
}

async function expectJsonResponse<T>(response: APIResponse, expectedStatus: number) {
  await expectJson(response, expectedStatus);
  return response.json() as Promise<T>;
}

async function expectPageJsonResponse<T>(response: PageResponse, expectedStatus: number) {
  const body = await response.text();
  expect(response.status(), body).toBe(expectedStatus);
  expect(response.headers()["content-type"] ?? "", body).toContain("application/json");
  return JSON.parse(body) as T;
}

async function expectEndpointAvailable(response: APIResponse, message: string) {
  const body = await response.text();
  expect(response.status(), `${message}: ${body}`).toBeLessThan(400);
}

function objectType(config: ConfigData, objectTypeKey: string) {
  const found = config.object_types?.find((item) => item.key === objectTypeKey);
  expect(found, `active config must include object type ${objectTypeKey}`).toBeTruthy();
  return found as ObjectTypeDefinition;
}

function objectTypeLabel(definition: ObjectTypeDefinition) {
  return definition.label ?? definition.plural_label ?? definition.key;
}

function fieldLabel(objectTypeDefinition: ObjectTypeDefinition, fieldKey: string) {
  const found = objectTypeDefinition.fields?.find((field) => field.key === fieldKey);
  expect(found, `${objectTypeDefinition.key} must include field ${fieldKey}`).toBeTruthy();
  return found?.label ?? humanize(fieldKey);
}

function configWithProductFieldRemoved(config: ConfigData) {
  const copy = JSON.parse(JSON.stringify(config)) as ConfigData;
  const productType = objectType(copy, "product");
  const removableField =
    productType.fields?.find((field) => !field.required) ?? productType.fields?.at(-1);
  expect(removableField, "product type needs at least one field for destructive removal").toBeTruthy();
  productType.fields = productType.fields?.filter((field) => field.key !== removableField?.key) ?? [];
  return {
    data: copy,
    removedFieldKey: removableField?.key ?? ""
  };
}

function timestamp() {
  const time = new Date().toISOString().replace(/[-:.TZ]/g, "");
  return `${time}-${Math.random().toString(36).slice(2, 8)}`;
}

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

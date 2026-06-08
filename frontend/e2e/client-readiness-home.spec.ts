import { expect, test } from "@playwright/test";

import {
  createRecord,
  ensureQaUsers,
  getJson,
  loginWithSession,
  requireHealthyStack,
  requireMutableQaTarget,
  type RecordPayload
} from "./support/qaApi";
import { readinessGate } from "./support/strictReadiness";

test.describe("client readiness Home overview", () => {
  test.beforeEach(async ({ request }) => {
    const health = await requireHealthyStack(request);
    readinessGate(!health.ok, health.message);
    const users = ensureQaUsers();
    readinessGate(!users.ok, users.ok ? "" : users.message);
  });

  test("operational overview uses live records and recent activity links are clickable", async ({
    context,
    page
  }) => {
    requireMutableQaTarget();
    const users = ensureQaUsers();
    if (!users.ok) {
      throw new Error(users.message);
    }
    const session = await loginWithSession(context, users.engineer);
    const stamp = timestamp();

    for (let index = 0; index < 6; index += 1) {
      await createRecord(session, "product", {
        commercial_name: `QA Home Clickable Product ${index + 1} ${stamp}`,
        internal_grade: `QA-HOME-${index + 1}-${stamp}`,
        resin_family: ["PP", "PE", "HDPE", "LDPE", "LLDPE"][index % 5],
        application: "Home overview route verification",
        color: "Natural"
      });
    }

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Operational Overview" })).toBeVisible();
    await expect(page.getByText("PE-1042")).toHaveCount(0);
    await expect(page.getByText("128")).toHaveCount(0);

    const recentActivity = page.getByRole("region", { name: "Recent Record Activity" });
    const recentLinks = recentActivity.getByRole("link");
    await expect(recentLinks.first()).toBeVisible();
    const firstRecentCode = (await recentLinks.first().textContent())?.trim();
    const liveRecords = await getJson<RecordPayload[]>(session.request, "/api/records/");
    const visibleRecentRecord = liveRecords.find((record) => record.code === firstRecentCode);
    if (!visibleRecentRecord) {
      throw new Error(`Expected visible recent record ${firstRecentCode} to exist in the live API.`);
    }
    const recentRecordLink = recentLinks.first();
    await expect(recentRecordLink).toBeVisible();
    await recentRecordLink.click();
    await expect(page).toHaveURL(new RegExp(`/records/${visibleRecentRecord.id}$`));
    await expect(page.getByRole("heading", { name: visibleRecentRecord.title })).toBeVisible();

    await page.goto("/");
    await page.getByRole("link", { name: /open records/i }).click();
    await expect(page).toHaveURL(/\/records$/);
    await page.goto("/");
    await page.getByRole("link", { name: /pending review/i }).click();
    await expect(page).toHaveURL(/\/tasks$/);
    await page.goto("/");
    await page.getByRole("link", { name: /controlled documents/i }).click();
    await expect(page).toHaveURL(/\/documents$/);
  });
});

function timestamp() {
  return `${new Date().toISOString().replace(/[-:.TZ]/g, "")}-${Math.random().toString(36).slice(2, 8)}`;
}

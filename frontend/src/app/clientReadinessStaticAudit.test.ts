import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

type BannedPattern = {
  file: string;
  pattern: RegExp;
  reason: string;
};

const bannedUiPatterns: BannedPattern[] = [
  {
    file: "src/app/routes.tsx",
    pattern: /recordQueue/,
    reason: "Home recent activity must come from live records."
  },
  {
    file: "src/app/routes.tsx",
    pattern: /PE-1042|PE-1038|PE-1029/,
    reason: "Home must not show static demo record codes."
  },
  {
    file: "src/app/routes.tsx",
    pattern: /value="128"|value="312"|value="17"|value="4"/,
    reason: "Home metric counts must be computed from API data."
  },
  {
    file: "src/app/routes.tsx",
    pattern: /Today|Yesterday|Jun 4/,
    reason: "Home recent activity dates must come from record timestamps."
  },
  {
    file: "src/app/routes.tsx",
    pattern: /Configure View/,
    reason: "Visible navigation fallback actions must not expose inert controls."
  },
  {
    file: "src/features/records/RecordList.tsx",
    pattern: /Configure View/,
    reason: "Records actions must be real navigation or mutation controls."
  },
  {
    file: "src/features/dashboards/DashboardPage.tsx",
    pattern: /Direct Load/,
    reason: "Dashboard status must describe user-visible state, not implementation mode."
  },
  {
    file: "src/features/documents/DocumentPanel.tsx",
    pattern: /href=\{document\.preview_url/,
    reason: "Preview must render inside the React app, not raw API JSON."
  },
  {
    file: "src/features/documents/DocumentPanel.tsx",
    pattern: /href=\{document\.audit_url/,
    reason: "Audit must render inside the React app, not raw API JSON."
  },
  {
    file: "src/features/documents/DocumentPanel.tsx",
    pattern: /Preview[\s\S]{0,240}\/api\/documents\/\$\{document\.id\}\/preview\//,
    reason: "Preview buttons must not navigate directly to raw API JSON."
  },
  {
    file: "src/features/documents/DocumentPanel.tsx",
    pattern: /Audit[\s\S]{0,240}\/api\/documents\/\$\{document\.id\}\/audit\//,
    reason: "Audit buttons must not navigate directly to raw API JSON."
  }
];

describe("client-readiness static UI audit", () => {
  it("blocks known fake operational data and raw JSON document actions", () => {
    const failures = bannedUiPatterns.flatMap(({ file, pattern, reason }) => {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      return pattern.test(source) ? [`${file}: ${reason} (${pattern})`] : [];
    });

    expect(failures).toEqual([]);
  });
});

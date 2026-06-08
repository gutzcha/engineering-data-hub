import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import type { TestInfo } from "@playwright/test";

import { REPO_ROOT } from "./qaApi";

export type BugSeverity = "Critical" | "High" | "Medium" | "Low";

export type BugFinding = {
  id: string;
  severity: BugSeverity;
  area: string;
  title: string;
  expected: string;
  actual: string;
  evidence: string;
};

export const QA_REPORT_PATH = path.join(REPO_ROOT, "docs", "qa", "client-readiness-qa-report.md");

export function ensureQaReport() {
  mkdirSync(path.dirname(QA_REPORT_PATH), { recursive: true });
  if (!existsSync(QA_REPORT_PATH)) {
    writeFileSync(
      QA_REPORT_PATH,
      [
        "# Client Readiness QA Report",
        "",
        "Date: 2026-06-08",
        "",
        "## Summary",
        "",
        "Automated and exploratory QA findings for the Plastic Engineering Data Hub.",
        "",
        "## Known Product Gaps To Verify During Execution",
        "",
        "### QA-GAP-001: Records Require Archive Instead Of Delete",
        "",
        "Severity: Critical",
        "",
        "Expected: Records cannot be deleted, but authorized users can archive records and archived records remain auditable.",
        "",
        "Actual: Code review shows `Record.Status` currently supports only `draft` and `released`, and `RecordViewSet` has no archive endpoint.",
        "",
        "Evidence: `backend/apps/records/models.py`, `backend/apps/records/views.py`",
        "",
        "### QA-GAP-002: Records Require Version Creation And Version Browsing",
        "",
        "Severity: Critical",
        "",
        "Expected: Users can create a new version of a record and inspect prior record versions.",
        "",
        "Actual: Code review shows document revisions exist, but no record revision/version model or endpoint is present.",
        "",
        "Evidence: `backend/apps/records/models.py`, `backend/apps/documents/models.py`",
        "",
        "## Findings",
        ""
      ].join("\n")
    );
  }
  return QA_REPORT_PATH;
}

export function recordFinding(finding: BugFinding, testInfo?: TestInfo) {
  ensureQaReport();
  const current = readFileSync(QA_REPORT_PATH, "utf-8");
  if (current.includes(`### ${finding.id}:`)) {
    return;
  }
  const evidence = testInfo?.outputDir
    ? `${finding.evidence}; Playwright output: ${path.relative(REPO_ROOT, testInfo.outputDir)}`
    : finding.evidence;
  writeFileSync(
    QA_REPORT_PATH,
    [
      current.trimEnd(),
      "",
      `### ${finding.id}: ${finding.title}`,
      "",
      `Severity: ${finding.severity}`,
      "",
      `Area: ${finding.area}`,
      "",
      `Expected: ${finding.expected}`,
      "",
      `Actual: ${finding.actual}`,
      "",
      `Evidence: ${evidence}`,
      ""
    ].join("\n")
  );
}

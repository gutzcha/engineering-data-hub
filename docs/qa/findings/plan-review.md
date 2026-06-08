# Plan Review Findings

Reviewer agent: `019ea61b-25be-7071-aef4-7f43b77546c6`

Date: 2026-06-08

## Verdict

Acceptable after changes. Not acceptable as-is for client handoff.

## Critical Corrections Integrated

- QA user setup must fail closed. If local user seeding is disabled and explicit credentials are missing, dependent tests must skip with a precise prerequisite message rather than attempting default credentials.
- Engineering QA users must not receive broad `can_admin` privileges. Separate Engineering, Configuration Admin, System Admin, and Read Only roles must be seeded.
- Multipart upload helpers must send a real file payload using a buffer, filename, and MIME type. Passing a string path is not sufficient for Django's `request.FILES`.
- Operations coverage must not use shallow "JSON and non-500" checks as proof of functionality. It must execute real or explicitly documented workflows for imports, projects, dashboards, backups, folder events, workflows, search, and exports.
- The suite must include the existing traceability E2E flow or port equivalent coverage into client-readiness specs.
- Search UI selectors must use the actual label, `Search query`, not a generic `searchbox` role.
- Route health must run after authentication for protected app areas and must cover direct reload behavior, including the `/admin` Vite proxy risk.
- The plan must include explicit tests for document DELETE/PATCH denial, invalid relationship targets, relationship delete/audit, configuration admin destructive publish denial, system admin confirmation publish, import dry-run/apply, XLSX exports, project board/timeline/dependency behavior, and document library gaps.
- Mutating QA runs must be guarded so they only run against local targets unless explicitly overridden.

## Improvement Actions Taken

- Added local-target guard to the environment contract and QA helper requirements.
- Updated planned package scripts to include `traceability.spec.ts`.
- Updated planned user seeding to create distinct roles and to skip rather than false-fail when prerequisites are absent.
- Updated multipart upload requirements to use a buffer-backed file payload.
- Replaced shallow operations success criteria with workflow-specific gates and explicit product-gap reporting.
- Updated search selector guidance to `getByLabel(/search query/i)`.
- Added duplicate-safe report writing and evidence-path requirements.

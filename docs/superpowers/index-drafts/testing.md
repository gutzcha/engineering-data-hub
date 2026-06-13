<!--
===
File Summary
Path: docs\superpowers\index-drafts\testing.md
Type: markdown
Purpose: Agent workflow and documentation for indexing, planning, and subagent coordination.
Primary responsibilities:
- Domain behavior is summarized for fast onboarding and avoids full-file reread.
- Core symbols: Testing Summary Draft
Inputs:
- Downstream and upstream interactions in the same domain.
Outputs:
- API payloads, records, side effects, or UI views depending on file role.
Dependencies:
- Shared runtime services and adjacent domain modules.
Known risks:
- Validate behavior after migrations, dependency upgrades, or contract changes.
===

-->

# Testing Summary Draft

- Scope: backend/tests, frontend/test, frontend/e2e
- Owner: quality-test-scan
- Indexed at: 2026-06-09T12:00:00Z

## Backend testing
- Command family:
  - `make test` (or `pytest` via Django test runner)
  - settings checks from `backend/tests/test_settings.py`
  - health contract from `backend/tests/test_health.py`
- Coverage hotspots: records, accounts permissions, backups, projects/dependencies, audits, relationships graph, imports, reports, search payloads, workflow engine.
- Files reviewed:
  - `backend/tests/accounts/test_permissions.py`
  - `backend/tests/records/test_records.py`
  - `backend/tests/records/test_codes.py`
  - `backend/tests/projects/test_projects.py`
  - `backend/tests/projects/test_dependencies.py`
  - `backend/tests/documents/test_revisions.py`
  - `backend/tests/documents/test_extraction.py`
  - `backend/tests/imports/test_excel_import.py`
  - `backend/tests/imports/test_folder_linking.py`
  - `backend/tests/backups/test_backup_manifest.py`
  - `backend/tests/folders/test_scanner.py`
  - `backend/tests/folders/test_templates.py`
  - `backend/tests/config_registry/test_api.py`
  - `backend/tests/config_registry/test_starter_config.py`
  - `backend/tests/config_registry/test_publish.py`
  - `backend/tests/relationships/test_graph.py`
  - `backend/tests/reports/test_saved_views.py`
  - `backend/tests/search/test_index_payloads.py`
  - `backend/tests/workflows/test_engine.py`
  - `backend/tests/e2e/test_traceability_flow.py`

## Frontend testing
- Unit/integration commands:
  - `make frontend-test`
  - Vitest through configured scripts (`frontend/package.json`).
- Key tests:
  - `frontend/src/app/App.test.tsx`
  - `frontend/src/features/*/*.test.tsx`
  - `frontend/src/lib/api.test.ts`
  - shared setup `frontend/src/test/setup.ts`

## E2E testing
- Playwright path: `frontend/e2e/*.ts`
- Main flow: `traceability.spec.ts`.
- E2E checks should run against a full compose stack with seeded data and search index available.

## Validation expectations
- API schema and route stability are primary acceptance criteria.
- Any new code should include/update tests in the nearest feature/module directory.
- Backend model/schema changes should include migration and targeted tests in `backend/tests/`.


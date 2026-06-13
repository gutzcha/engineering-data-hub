# Feature Inventory and Test Execution Plan

Date: 2026-06-09
Request: List every feature, define a test plan per feature, and execute the plan.
Owner style: subagent-inspired execution (backend-scan, frontend-scan, qa-e2e)

## 1) Every Feature in This App

### A. Frontend Features (from `frontend/src/app/routes.tsx` and `features/`)

1. **Operational Overview** (Home/Dashboard Landing)
   - Route: `/`
   - Files: `frontend/src/app/routes.tsx`, `frontend/src/app/App.tsx`, `frontend/src/components/*`

2. **Authentication Session UI**
   - Route: `/login`
   - Files: `frontend/src/features/auth/LoginPage.tsx`

3. **Records Browse / Detail / Create**
   - Routes: `/records`, `/records/new`, `/records/:recordId`
   - Files: `frontend/src/features/records/RecordList.tsx`, `RecordCreate.tsx`, `RecordDetail.tsx`, `DynamicRecordForm.tsx`, `EntityGraphPanel.tsx`

4. **Project Workspace**
   - Routes: `/projects`, `/projects/:projectId`
   - Files: `frontend/src/features/projects/ProjectList.tsx`, `ProjectDetail.tsx`, `ProjectBoard.tsx`, `ProjectTimeline.tsx`, `WorkloadView.tsx`

5. **Import Intake (Excel/CSV + Mapping)**
   - Route: `/imports`
   - Files: `frontend/src/features/imports/ImportWizard.tsx`

6. **Document Library and Detail**
   - Routes: `/documents`, `/documents/:documentId`
   - Files: `frontend/src/features/documents/DocumentPanel.tsx`

7. **Search Discovery**
   - Route: `/search`
   - Files: `frontend/src/features/search/SearchPage.tsx`

8. **Reporting and Dashboard View Builder**
   - Route: `/dashboards`
   - Files: `frontend/src/features/dashboards/DashboardPage.tsx`, `SavedViewBuilder.tsx`

9. **Audit Timeline**
   - Route: `/audit`
   - Files: `frontend/src/features/audit/AuditTimeline.tsx`

10. **Task Inbox and Review Queue**
    - Routes: `/tasks`, `/tasks/folder-events`, `/tasks/folder-events/:eventId`
    - Files: `frontend/src/features/workflows/TaskInbox.tsx`, `frontend/src/features/folders/FolderReviewInbox.tsx`

11. **Admin Configuration Studio**
    - Route: `/admin`
    - Files: `frontend/src/features/admin-config/ConfigWorkspace.tsx`, `ConfigWorkspace` sub-editors (`ObjectTypeEditor.tsx`, `FieldEditor.tsx`, `FolderTemplateEditor.tsx`, `FormLayoutEditor.tsx`, `WorkflowEditor.tsx`)

12. **System Shell / Navigation Surface**
    - Shared routing and layout behavior
    - Files: `frontend/src/app/App.tsx`, `frontend/src/app/routes.tsx`, `frontend/src/components/AppLayout.tsx`, `DataTable.tsx`, `StatusBadge.tsx`

### B. Backend/API Features (from `backend/apps` + root urls)

13. **Account & Identity**
    - URLs: `/api/accounts/`
    - Files: `backend/apps/accounts/*`, `backend/apps/accounts/tests?`

14. **Audit Logging API**
    - URLs: `/api/audit/`
    - Files: `backend/apps/audit/*`

15. **Backup Orchestration API**
    - URLs: `/api/backups/`
    - Files: `backend/apps/backups/*`

16. **Configuration Registry API**
    - URLs: `/api/config/`
    - Files: `backend/apps/config_registry/*`

17. **Document Management API**
    - URLs: `/api/documents/`
    - Files: `backend/apps/documents/*`

18. **Folder Events / Change Log API**
    - URLs: `/api/folder-events/`
    - Files: `backend/apps/folders/*`

19. **Imports API**
    - URLs: `/api/imports/...`
    - Files: `backend/apps/imports/*`

20. **Projects API**
    - URLs: `/api/projects/`
    - Files: `backend/apps/projects/*`

21. **Records API**
    - URLs: `/api/records/`
    - Files: `backend/apps/records/*`

22. **Relationship API**
    - URLs: `/api/relationships/`
    - Files: `backend/apps/relationships/*`

23. **Reports / Saved Views / Dashboards API**
    - URLs: `/api/reports/` and `/api/dashboards/`
    - Files: `backend/apps/reports/*`

24. **Search API**
    - URLs: `/api/search/`
    - Files: `backend/apps/search/*`

25. **Workflow Engine API and Runtime**
    - URLs: `/api/workflow-tasks/`, `/api/records/<id>/workflow/`
    - Files: `backend/apps/workflows/*`

26. **Health Endpoint**
    - URL: `/api/health/`
    - Files: `backend/apps/api/views.py`, `backend/apps/api/`

27. **Cross-cutting Runtime/Runtime Ops**
    - Files: `backend/plastic_hub/*`, task queue and settings modules

---

## 2) Test Plan (Per-Feature)

### Backend subagent plan

- **accounts**
  - Test: `backend/tests/accounts/test_permissions.py`

- **audit**
  - Test: `backend/tests/audit/test_audit_log.py`

- **backups**
  - Test: `backend/tests/backups/test_backup_manifest.py`

- **config_registry**
  - Tests: `backend/tests/config_registry/test_api.py`, `backend/tests/config_registry/test_starter_config.py`, `backend/tests/config_registry/test_publish.py`

- **documents**
  - Tests: `backend/tests/documents/test_revisions.py`, `backend/tests/documents/test_extraction.py`

- **folders**
  - Tests: `backend/tests/folders/test_scanner.py`, `backend/tests/folders/test_templates.py`

- **imports**
  - Tests: `backend/tests/imports/test_excel_import.py`, `backend/tests/imports/test_folder_linking.py`

- **projects**
  - Tests: `backend/tests/projects/test_projects.py`, `backend/tests/projects/test_dependencies.py`

- **records**
  - Tests: `backend/tests/records/test_records.py`, `backend/tests/records/test_codes.py`

- **relationships**
  - Test: `backend/tests/relationships/test_graph.py`

- **reports**
  - Test: `backend/tests/reports/test_saved_views.py`

- **search**
  - Test: `backend/tests/search/test_index_payloads.py`

- **workflows**
  - Test: `backend/tests/workflows/test_engine.py`

- **api health/settings smoke**
  - Tests: `backend/tests/test_health.py`, `backend/tests/test_settings.py`

- **Traceability E2E backend flow**
  - Test: `backend/tests/e2e/test_traceability_flow.py`

### Frontend subagent plan

- **Authentication**
  - Test: `frontend/src/features/auth/LoginPage.test.tsx`

- **Shell + navigation**
  - Test: `frontend/src/app/App.test.tsx`

- **Records**
  - Tests: `frontend/src/features/records/RecordCreate.test.tsx`, `frontend/src/features/records/RecordDetail.test.tsx`

- **Projects**
  - Tests: `frontend/src/features/projects/ProjectList.test.tsx`, `frontend/src/features/projects/ProjectBoard.test.tsx`, `frontend/src/features/projects/ProjectTimeline.test.tsx`

- **Imports**
  - Test: `frontend/src/features/imports/ImportWizard.test.tsx`

- **Document Library**
  - No dedicated component test currently; covered indirectly by app-level route smoke from `App.test.tsx` if present.

- **Search**
  - Test: `frontend/src/features/search/SearchPage.test.tsx`

- **Dashboards**
  - Test: `frontend/src/features/dashboards/DashboardPage.test.tsx`

- **Audit**
  - No dedicated audit feature test currently (file exists, route coverage via app smoke).

- **Tasks / Queue / Folder review**
  - Test: `frontend/src/features/workflows/TaskInbox.test.tsx`, `frontend/src/features/folders/FolderReviewInbox.test.tsx`

- **Admin Config workspace**
  - Test: `frontend/src/features/admin-config/ConfigWorkspace.test.tsx`

- **API transport contract**
  - Test: `frontend/src/lib/api.test.ts`

### E2E subagent plan

- Run `frontend/e2e/traceability.spec.ts` as end-to-end feature path through records/projects/documents/search/audits/tasks where possible.

---

## 3) Execution Commands

Backend (feature groups):
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/accounts`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/audit`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/backups`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/config_registry`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/documents`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/folders`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/imports`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/projects`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/records`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/relationships`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/reports`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/search`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/workflows`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/test_health.py backend/tests/test_settings.py`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend pytest backend/tests/e2e/test_traceability_flow.py`

Frontend (feature groups):
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/app/App.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/auth/LoginPage.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/records/RecordCreate.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/records/RecordDetail.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/projects/ProjectList.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/projects/ProjectBoard.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/projects/ProjectTimeline.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/imports/ImportWizard.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/search/SearchPage.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/dashboards/DashboardPage.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/folders/FolderReviewInbox.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/workflows/TaskInbox.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/features/admin-config/ConfigWorkspace.test.tsx`
- `docker compose -f compose.yaml -f compose.dev.yaml run --rm frontend npm test -- --run src/lib/api.test.ts`

E2E:
- Start app stack as required by README, then run:
  - `cd frontend && E2E_USERNAME=<user> E2E_PASSWORD=<pass> npx playwright test e2e/traceability.spec.ts`

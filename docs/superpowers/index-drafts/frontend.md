<!--
===
File Summary
Path: docs\superpowers\index-drafts\frontend.md
Type: markdown
Purpose: Agent workflow and documentation for indexing, planning, and subagent coordination.
Primary responsibilities:
- Domain behavior is summarized for fast onboarding and avoids full-file reread.
- Core symbols: Frontend Summary Draft
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

# Frontend Summary Draft

- Scope: frontend/
- Owner: frontend-scan
- Indexed at: 2026-06-09T12:00:00Z
- Purpose: map route entry, feature ownership, API usage, and test surface for agent onboarding.

## Routes and Entry Points
- `frontend/src/main.tsx` mounts app and global providers.
- `frontend/src/app/routes.tsx` defines route tree and permission-aware route guards.
- `frontend/src/app/App.tsx` is shell for layout orchestration and route outlet composition.
- Route map references major pages:
  - `/` dashboard
  - `/projects/*`
  - `/records/*`
  - `/documents/*`
  - `/imports/*`
  - `/search`
  - `/admin/*`
  - `/workflows/*`

## Domain Features

### Auth and shell
- `frontend/src/features/auth/LoginPage.tsx` and `LoginPage.test.tsx`.
- `frontend/src/components/AppLayout.tsx`, `StatusBadge.tsx`, `DataTable.tsx` provide shared shell/data widgets.

### Projects
- `frontend/src/features/projects/ProjectList.tsx`
- `frontend/src/features/projects/ProjectDetail.tsx`
- `frontend/src/features/projects/ProjectBoard.tsx`
- `frontend/src/features/projects/ProjectTimeline.tsx`
- `frontend/src/features/projects/WorkloadView.tsx`
- Tests: `ProjectList.test.tsx`, `ProjectBoard.test.tsx`, `ProjectTimeline.test.tsx`.

### Records
- `frontend/src/features/records/RecordList.tsx`
- `frontend/src/features/records/RecordCreate.tsx`
- `frontend/src/features/records/RecordDetail.tsx`
- `frontend/src/features/records/DynamicRecordForm.tsx`
- `frontend/src/features/records/EntityGraphPanel.tsx`
- Test: `RecordDetail.test.tsx`, `RecordCreate.test.tsx`.

### Documents and folders
- `frontend/src/features/documents/DocumentPanel.tsx`
- `frontend/src/features/folders/FolderPanel.tsx`
- `frontend/src/features/folders/FolderReviewInbox.tsx`
- Test: `FolderReviewInbox.test.tsx`.

### Imports
- `frontend/src/features/imports/ImportWizard.tsx`
- Test: `ImportWizard.test.tsx`.

### Dashboards and reporting
- `frontend/src/features/dashboards/DashboardPage.tsx`
- `frontend/src/features/dashboards/SavedViewBuilder.tsx`
- Test: `DashboardPage.test.tsx`.

### Audit and search
- `frontend/src/features/audit/AuditTimeline.tsx`
- `frontend/src/features/search/SearchPage.tsx`
- Test: `SearchPage.test.tsx`.

### Workflows
- `frontend/src/features/workflows/WorkflowPanel.tsx`
- `frontend/src/features/workflows/TaskInbox.tsx`
- Test: `TaskInbox.test.tsx`.

### Admin config
- `frontend/src/features/admin-config/ConfigWorkspace.tsx`
- `ObjectTypeEditor.tsx`, `FieldEditor.tsx`, `FolderTemplateEditor.tsx`, `FormLayoutEditor.tsx`, `WorkflowEditor.tsx`
- Test: `ConfigWorkspace.test.tsx`.

### End-to-end and shared API
- E2E: `frontend/e2e/traceability.spec.ts`.
- API client layer: `frontend/src/lib/api.ts` with tests `frontend/src/lib/api.test.ts`.
- Shared test harness: `frontend/src/test/setup.ts`.

## State and Data Fetching
- API calls are centralized in `src/lib/api.ts` and consumed by feature modules.
- UI state is local component state with route-scope effects; minimal shared global store.
- Data lifecycle: mount -> API request -> local state -> render -> action mutations.

## API and backend touchpoints
- Primary endpoints: accounts, projects, records, folders, documents, imports, search, audits, reports, workflows, configs.
- API payload shape is shaped in backend DRF serializers and consumed by forms, tables, and timeline/list pages.
- Test coverage includes API-client unit tests plus key feature behavior tests.

## Testing Summary
- Unit/integration tests in `frontend/src/**/**/*.test.tsx`.
- E2E tests under `frontend/e2e/*.ts`.
- Critical paths: login, project list/detail, dashboard builder, search, folder review, workflow task inbox, import wizard.


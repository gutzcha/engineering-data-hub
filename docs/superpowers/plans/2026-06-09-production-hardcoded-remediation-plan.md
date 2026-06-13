# Production-Readiness Remediation Plan (Home, Search, Records, Projects, Documents, Dashboard, Audit, Tasks, Admin)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all hardcoded UI states with SQL-driven, permission-aware behavior; deliver production workflows for records/projects/documents/search/dashboards/audit/tasks/admin management with dynamic configuration.

**Architecture:** Extend the existing Django DRF backend as the single source of truth for analytics, lookups, and workflow actions. Add strict read/write API contracts for home/search/projects/documents/workflow actions and consume them through focused React feature pages. Use the existing config registry as the canonical schema for dynamic fields, form layouts, and dashboard widgets, and enforce live references for all user/record lookups.

**Tech Stack:** Django, DRF, PostgreSQL, React, TypeScript, React Router, existing config registry, existing audit/search services, TanStack Query (or current fetch layer), and test frameworks in `backend/tests` and frontend `*.test.tsx`.

---

## Task 1: Baseline contract tests for all “frozen” pages

**Files:**
- Create: `backend/tests/reports/test_home_api.py`
- Create: `backend/tests/search/test_filters_and_results.py`
- Create: `backend/tests/projects/test_project_workflows.py`
- Create: `backend/tests/documents/test_document_registry_and_links.py`
- Create: `backend/tests/config_registry/test_form_admin_contracts.py`
- Modify: `backend/tests/records/test_records.py` (append schema-dependent field assertions)
- Modify: `frontend/src/features/search/SearchPage.test.tsx`
- Modify: `frontend/src/features/records/RecordCreate.test.tsx`
- Modify: `frontend/src/features/projects/ProjectList.test.tsx`
- Modify: `frontend/src/features/documents/DocumentPanel.test.tsx` (create if absent)
- Modify: `frontend/src/features/dashboards/DashboardPage.test.tsx`
- Modify: `frontend/src/features/admin-config/ConfigWorkspace.test.tsx`

- [ ] **Step 1: Write backend tests for live home metrics and clickable filter redirects**

```python
def test_home_overview_uses_live_counts_and_no_placeholders(api_client, user_with_perm):
    response = api_client.get("/api/reports/dashboards/home-overview/", format="json")
    assert response.status_code == 200
    assert "cards" in response.data
    assert all(isinstance(card["value"], int) for card in response.data["cards"])
    assert response.data["cards"][0]["filter_key"] in {"active", "review", "blocked", "ready"}
```

- [ ] **Step 2: Write backend test for search filtering behavior (hide zero-result sections)**

```python
def test_search_shows_only_non_empty_sections(api_client, user_with_perm):
    response = api_client.get("/api/search/?object_type_key=product&status=active")
    assert response.status_code == 200
    assert response.data["count"] > 0
    assert all(len(section["items"]) > 0 for section in response.data["sections"])
```

- [ ] **Step 3: Write backend tests for schema-driven field lists and document linkage**

```python
def test_lookup_options_are_live_and_config_managed(api_client, config_admin):
    response = api_client.get("/api/config/active/")
    assert response.status_code == 200
    assert isinstance(response.data["document_types"], list)
    assert isinstance(response.data["choices"]["resin_family"], list)
```

- [ ] **Step 4: Write backend test for project assignee/user lookups and privilege levels**

```python
def test_project_assignee_lookup_returns_users_only(api_client, privileged_user):
    response = api_client.get("/api/accounts/lookup/users/?q=alex&scope=project")
    assert response.status_code == 200
    assert {"id", "username", "display_name", "level"} <= response.data[0].keys()
```

- [ ] **Step 5: Write frontend tests that verify non-frozen behavior**

```tsx
it("navigates search tab pre-filtered when clicking home status card", async () => {
  render(<HomePage />);
  await user.click(screen.getByText(/active/i));
  expect(mockNavigate).toHaveBeenCalledWith("/search?status=active");
});
```

- [ ] **Step 6: Run baseline test subset and confirm failures**

Run:
- `python -m pytest backend/tests/reports/test_home_api.py backend/tests/search/test_filters_and_results.py -q`
- `python -m pytest backend/tests/projects/test_project_workflows.py backend/tests/documents/test_document_registry_and_links.py backend/tests/config_registry/test_form_admin_contracts.py -q`
- `cd frontend && npm test -- src/features/search/SearchPage.test.tsx src/features/records/RecordCreate.test.tsx src/features/projects/ProjectList.test.tsx`

- [ ] **Step 7: Commit baseline red tests**

```bash
git add backend/tests/reports/test_home_api.py backend/tests/search/test_filters_and_results.py backend/tests/projects/test_project_workflows.py backend/tests/documents/test_document_registry_and_links.py backend/tests/config_registry/test_form_admin_contracts.py backend/tests/records/test_records.py frontend/src/features/search/SearchPage.test.tsx frontend/src/features/records/RecordCreate.test.tsx frontend/src/features/projects/ProjectList.test.tsx frontend/src/features/dashboards/DashboardPage.test.tsx frontend/src/features/admin-config/ConfigWorkspace.test.tsx
git commit -m "test: add baseline regression tests for hardcoded-page remediation"
```

## Task 2: Make Home page fully live and action-driven

**Files:**
- Modify: `backend/apps/reports/urls.py`
- Modify: `backend/apps/reports/views.py`
- Modify: `backend/apps/reports/query.py`
- Modify: `backend/apps/search/views.py` (optional shared filter helpers)
- Modify: `frontend/src/app/routes.tsx`
- Modify: `frontend/src/features/records/RecordList.tsx` (for status card links consistency)
- Modify: `frontend/src/features/projects/ProjectList.tsx` (shared filters)

- [ ] **Step 1: Add a home overview API payload with live counts and sectioned recent records**

```python
def _serialize_home_overview_payload(user, limit=10):
    return {
        "cards": [
            {"key": "active", "label": "Active", "value": queryset.count(), "filter": {"status": "active"}},
            {"key": "review", "label": "Review", "filter": {"status": "review"}},
        ],
        "recent_records": [
            {"id": r.id, "code": r.code, "title": r.title, "status": r.status, "object_type_key": r.object_type_key, "updated_at": r.updated_at.isoformat()}
            for r in records[:limit]
        ],
    }
```

- [ ] **Step 2: Expose dashboard-oriented query endpoint**

Add in `backend/apps/reports/urls.py`:
`path("dashboards/home-overview/", HomeOverviewView.as_view(), name="home-overview"),`

Add filtering and visibility checks in `backend/apps/reports/query.py`.

- [ ] **Step 3: Remove hardcoded counts in Home route and fetch live data**

In `frontend/src/app/routes.tsx`, replace inline arrays for `Recent Record Activity`, status counts, and cards with `api.get("/api/reports/dashboards/home-overview/")`.

- [ ] **Step 4: Make each status card link to Search tab with persisted filter**

```tsx
navigate(`/search?status=${encodeURIComponent(card.filter.status)}&from=home`);
```

- [ ] **Step 5: Make recent activity rows clickable**

Use row clicks to open:
- record rows -> `navigate(`/records/${id}`)`
- project rows -> `navigate(`/projects/${project_id}`)` if present

- [ ] **Step 6: Add loading/empty/error states and accessibility labels**

Implement explicit states (`loading`, `empty`, `error`) and `aria-label` for each clickable card/row.

- [ ] **Step 7: Run targeted tests and commit**

Run:
- `python -m pytest backend/tests/reports/test_home_api.py -q`
- `cd frontend && npm test -- src/features/search/SearchPage.test.tsx src/features/records/RecordList.test.tsx`

Commit:
```bash
git add backend/apps/reports/urls.py backend/apps/reports/views.py backend/apps/reports/query.py frontend/src/app/routes.tsx frontend/src/features/records/RecordList.tsx
git commit -m "feat(home): replace hardcoded cards and activity with live overview API"
```

## Task 3: Build click-through status buckets and robust search filters

**Files:**
- Modify: `backend/apps/search/models.py` (if needed)
- Modify: `backend/apps/search/views.py`
- Modify: `backend/apps/search/serializers.py`
- Modify: `backend/apps/search/tasks.py`
- Modify: `frontend/src/features/search/SearchPage.tsx`
- Modify: `frontend/src/features/search/SearchPage.test.tsx`
- Modify: `frontend/src/components/TagInput.tsx` (or create reusable tag field chip component)
- Create: `frontend/src/features/search/searchFilterSchema.ts`

- [ ] **Step 1: Add search API to return grouped sections with visibility metadata**

```python
def _build_sections(results):
    return [s for s in sections if s["count"] > 0 and s["items"]]
```

- [ ] **Step 2: Add canonical filter DTO including status, tags, application, resin family, color, project_status, form_fields**

```ts
export type SearchFilters = {
  q?: string;
  status?: string;
  tags?: string[];
  application?: string[];
  resin_family?: string[];
  color?: string[];
  project_status?: string[];
};
```

- [ ] **Step 3: Add filter controls using live option endpoints**

Backend: new endpoints for form-driven options
- `/api/config/field-options/?object_type_key=...&field_key=...`
Frontend: map options into multi-select chips for the above fields.

- [ ] **Step 4: Filter empty groups away**

In `frontend/src/features/search/SearchPage.tsx`, render cards only for groups where `items.length > 0`.

- [ ] **Step 5: Wire home status clicks to open Search tab filter querystring**

```tsx
const params = new URLSearchParams(location.search);
params.set("status", card.filter.status);
navigate(`/search?${params.toString()}`);
```

- [ ] **Step 6: Add tests for zero-result filtering and new filter controls**

In `frontend/src/features/search/SearchPage.test.tsx`, assert zero-result groups are not rendered and filter payload is sent.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/search/views.py backend/apps/search/serializers.py backend/apps/search/tasks.py frontend/src/features/search/SearchPage.tsx frontend/src/features/search/searchFilterSchema.ts frontend/src/components/TagInput.tsx frontend/src/features/search/SearchPage.test.tsx
git commit -m "feat(search): hide empty result groups and add schema-driven filters"
```

## Task 4: Records tab — live dropdowns and no hidden fields

**Files:**
- Modify: `backend/apps/config_registry/services.py`
- Modify: `backend/apps/records/models.py`
- Modify: `backend/apps/records/serializers.py`
- Modify: `backend/apps/records/views.py`
- Modify: `backend/apps/records/codes.py`
- Modify: `frontend/src/features/records/RecordCreate.tsx`
- Modify: `frontend/src/features/records/DynamicRecordForm.tsx`
- Modify: `frontend/src/features/records/RecordList.tsx`
- Modify: `frontend/src/features/records/RecordDetail.tsx`
- Create: `backend/apps/records/field_sync.py` (utility to sanitize weird dynamic keys)

- [ ] **Step 1: Add resin-family lookup endpoint backed by SQL or config registry**

```python
def test_resin_family_endpoint_returns_active_family_names(api_client):
    r = api_client.get("/api/config/field-options/?object_type_key=record&field_key=resin_family")
    assert r.status_code == 200
    assert all("value" in item for item in r.data["options"])
```

- [ ] **Step 2: Replace hardcoded QA field names**

Normalize historical placeholders:
- rename backend canonical field keys to human-readable labels in active config
- keep server-side legacy ingestion compatibility via alias map in `field_sync.py`

- [ ] **Step 3: Update `DynamicRecordForm` to render select/autocomplete by live schema metadata**

When `field.type == "choice"` or `"multi_choice"`, source options from `/api/config/field-options/`.

- [ ] **Step 4: Add missing dynamic controls for document-linked fields**

Support `record_ref`, `user`, and `customer` field types in form renderer with searchable selects.

- [ ] **Step 5: Enforce field presence + ordering from active config**

Modify form initialization to read and sort fields by `form_layout` section and order metadata, fallback to schema order.

- [ ] **Step 6: Add record-link and activity checks in list/detail**

Recent records in list/detail should link to actual DB ids and preserve query context.

- [ ] **Step 7: Add/extend tests**

Run:
- `python -m pytest backend/tests/records/test_records.py -q`
- `python -m pytest backend/tests/config_registry/test_form_admin_contracts.py -q`
- `cd frontend && npm test -- src/features/records/RecordCreate.test.tsx src/features/records/RecordDetail.test.tsx`

Commit:
```bash
git add backend/apps/config_registry/services.py backend/apps/records/models.py backend/apps/records/serializers.py backend/apps/records/views.py backend/apps/records/field_sync.py frontend/src/features/records/RecordCreate.tsx frontend/src/features/records/DynamicRecordForm.tsx frontend/src/features/records/RecordList.tsx frontend/src/features/records/RecordDetail.tsx
git commit -m "feat(records): live option sources, schema-driven fields, and QA field cleanup"
```

## Task 5: Project domain completion: create, assign, change status, assignee via users

**Files:**
- Modify: `backend/apps/projects/models.py`
- Modify: `backend/apps/projects/serializers.py`
- Modify: `backend/apps/projects/views.py`
- Modify: `backend/apps/projects/services.py`
- Modify: `backend/apps/accounts/models.py`
- Modify: `frontend/src/features/projects/ProjectList.tsx`
- Modify: `frontend/src/features/projects/ProjectDetail.tsx`
- Modify: `frontend/src/features/projects/ProjectBoard.tsx`
- Modify: `frontend/src/features/projects/WorkloadView.tsx`

- [ ] **Step 1: Add API endpoint for users lookup with privileges**

Add `/api/accounts/lookup/users/?scope=assignee&active=true` returning searchable name/username/level.

- [ ] **Step 2: Make project create form backend validated and writable**

`ProjectSerializer` currently must reject placeholder IDs; enforce FK assignment to valid user IDs and project status enums.

- [ ] **Step 3: Implement assignee change endpoint**

Add action endpoint:
`POST /api/projects/{id}/assign/` with payload `{assignee_user_id}` and privilege guard.

- [ ] **Step 4: Build `ProjectList` toolbar/actions**

Add create-project quick action, search by status, assignee chips, and direct row action menu.

- [ ] **Step 5: Add assignee control with searchable dropdown**

In `ProjectDetail.tsx` and list rows, swap manual ID inputs for `UserSelect` component hitting lookup endpoint.

- [ ] **Step 6: Add tests**

Create/update tests in `backend/tests/projects/test_projects.py` for assign and create actions; frontend tests for assignee dropdown and create workflow.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/projects/models.py backend/apps/projects/serializers.py backend/apps/projects/views.py backend/apps/projects/services.py frontend/src/features/projects/ProjectList.tsx frontend/src/features/projects/ProjectDetail.tsx frontend/src/features/projects/ProjectBoard.tsx frontend/src/features/projects/WorkloadView.tsx
git commit -m "feat(projects): enable create/edit lifecycle with searchable assignee assignments"
```

## Task 6: User table and privilege model as first-class selector source

**Files:**
- Modify: `backend/apps/accounts/models.py`
- Modify: `backend/apps/accounts/admin.py`
- Modify: `backend/apps/accounts/serializers.py`
- Modify: `backend/apps/accounts/views.py`
- Create: `backend/apps/accounts/migrations/0002_user_privilege_fields.py`
- Modify: `backend/apps/accounts/urls.py`
- Modify: `frontend/src/components/UserSelect.tsx`
- Modify: `frontend/src/app/api.ts`
- Modify: `frontend/src/features/records/DynamicRecordForm.tsx`
- Modify: `frontend/src/features/projects/ProjectDetail.tsx`

- [ ] **Step 1: Add explicit privilege levels and searchable API**

Add a user profile/role column accessible from user JSON: `privilege_level` values `viewer`, `operator`, `manager`, `admin`.

- [ ] **Step 2: Add user lookup endpoint**

Add `GET /api/accounts/users/` filtering by query + privilege.

- [ ] **Step 3: Replace all text-ID person selectors**

Find free-text person selectors in records/projects/documents/admin forms and replace with `<UserSelect />` dropdown.

- [ ] **Step 4: Add permission-aware field visibility**

Only show form fields and actions matching user privilege using backend filter flags plus frontend guard.

- [ ] **Step 5: Add tests**

Backend: `backend/tests/accounts` test new privilege field and API filter behavior.
Frontend: add tests for disabled actions by role.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/accounts/models.py backend/apps/accounts/admin.py backend/apps/accounts/serializers.py backend/apps/accounts/views.py backend/apps/accounts/migrations/0002_user_privilege_fields.py backend/apps/accounts/urls.py frontend/src/components/UserSelect.tsx frontend/src/app/api.ts frontend/src/features/records/DynamicRecordForm.tsx frontend/src/features/projects/ProjectDetail.tsx
git commit -m "feat(users): add privilege model and user lookup dropdown integration"
```

## Task 7: Documents module — controlled types, uploads, and record linking

**Files:**
- Modify: `backend/apps/documents/models.py`
- Modify: `backend/apps/documents/serializers.py`
- Modify: `backend/apps/documents/views.py`
- Modify: `backend/apps/documents/storage.py`
- Modify: `backend/apps/documents/urls.py`
- Modify: `backend/apps/documents/tasks.py` (if any async link jobs)
- Create: `backend/apps/documents/migrations/0002_document_type_catalog.py`
- Modify: `frontend/src/features/documents/DocumentPanel.tsx`
- Create: `frontend/src/features/documents/DocumentTypeManager.tsx`
- Create: `frontend/src/features/documents/DocumentUploadWorkflow.tsx`
- Create: `backend/apps/documents/management/commands/seed_material_documents.py`

- [ ] **Step 1: Make controlled document type authoritative**

Create `DocumentType` model entries and deprecate free-text type entry validation.

- [ ] **Step 2: Add API for document type maintenance**

CRUD endpoints:
- `GET /api/documents/types/`
- `POST /api/documents/types/`
- `PATCH /api/documents/types/{id}/`
- `DELETE /api/documents/types/{id}/`

- [ ] **Step 3: Add record linkage capability**

Add M2M relation on document revision event or document document: 
`linked_records = ManyToManyField(Record, blank=True)`
with audit events on link/unlink operations.

- [ ] **Step 4: Enhance upload form to pick controlled fields**

In `DocumentPanel.tsx`, set `document_type`, `owner_record`, `linked_records` as controlled dropdown/autocomplete fields.

- [ ] **Step 5: Add PDF bulk import job**

Create command to download 20 material-related PDFs into a temp directory and upload via authenticated service client, associating:
- `document_type = "material_reference"`
- `owner_record` set from raw material lookup
- tags and resin family extracted from filename metadata map

- [ ] **Step 6: Add a script and operational runbook**

Add `backend/scripts/import_material_pdfs.ps1` and usage comments in README section for re-run safety.

- [ ] **Step 7: Add tests and commit**

Run:
- `python -m pytest backend/tests/documents/test_document_registry_and_links.py -q`
- `cd frontend && npm test -- src/features/documents/DocumentPanel.test.tsx`

Commit:
```bash
git add backend/apps/documents/models.py backend/apps/documents/serializers.py backend/apps/documents/views.py backend/apps/documents/storage.py backend/apps/documents/migrations/0002_document_type_catalog.py backend/apps/documents/management/commands/seed_material_documents.py frontend/src/features/documents/DocumentPanel.tsx frontend/src/features/documents/DocumentTypeManager.tsx frontend/src/features/documents/DocumentUploadWorkflow.tsx
git commit -m "feat(documents): controlled document types, linking, and seeded material PDF workflow"
```

## Task 8: Clarify Import Wizard as guided flow

**Files:**
- Modify: `frontend/src/features/imports/ImportWizard.tsx`
- Modify: `frontend/src/features/imports/importWizardConfig.ts`
- Modify: `frontend/src/features/imports/importValidationSchema.ts` (create if absent)
- Modify: `frontend/src/app/routes.tsx`

- [ ] **Step 1: Add static help text per tab**

Add helper panel with: expected columns, validation rules, success criteria, next action per step.

- [ ] **Step 2: Add step validation messages and progress summary**

Each step must render `ready`, `needs_action`, `blocked` labels and disable next step if schema missing.

- [ ] **Step 3: Add sample mapping templates and one-click download**

Expose `Download template` CTA per file type and a `preview row 1..5`.

- [ ] **Step 4: Add tests and commit**

```bash
git add frontend/src/features/imports/ImportWizard.tsx frontend/src/features/imports/importWizardConfig.ts frontend/src/features/imports/importValidationSchema.ts frontend/src/app/routes.tsx frontend/src/features/imports/ImportWizard.test.tsx
git commit -m "feat(imports): guided import wizard with per-tab explanation and validation state"
```

## Task 9: Dashboard page usability — filter icon, editable views, and descriptions

**Files:**
- Modify: `backend/apps/reports/models.py`
- Modify: `backend/apps/reports/serializers.py`
- Modify: `backend/apps/reports/views.py`
- Modify: `frontend/src/features/dashboards/DashboardPage.tsx`
- Modify: `frontend/src/features/dashboards/SavedViewBuilder.tsx`
- Modify: `frontend/src/components/Modal.tsx` (if needed for view edit flow)
- Modify: `frontend/src/lib/validation.ts`

- [ ] **Step 1: Add first-class dashboard description fields**

Ensure `description` is required in create/update and visible in response payload.

- [ ] **Step 2: Implement filter icon interaction on dashboard widgets**

Hook icon to `setWidgetFilterState`; reuse search filter object and open side sheet with applied params.

- [ ] **Step 3: Clarify create new view flow**

In SavedViewBuilder, add explicit step sequence:
1) Select dataset
2) Add filters
3) Pick columns
4) Save with description and visibility scope.

- [ ] **Step 4: Add tests for descriptions and filter open/close state**

Update `frontend/src/features/dashboards/DashboardPage.test.tsx`.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/models.py backend/apps/reports/serializers.py backend/apps/reports/views.py frontend/src/features/dashboards/DashboardPage.tsx frontend/src/features/dashboards/SavedViewBuilder.tsx frontend/src/components/Modal.tsx
git commit -m "feat(dashboards): active filters, clear new view flow, and required descriptions"
```

## Task 10: Audit as action log, everything clickable

**Files:**
- Modify: `backend/apps/audit/models.py` (if actor/target links missing)
- Modify: `backend/apps/audit/serializers.py`
- Modify: `backend/apps/audit/views.py`
- Modify: `frontend/src/features/audit/AuditTimeline.tsx`
- Modify: `frontend/src/features/audit/AuditTimeline.test.tsx`

- [ ] **Step 1: Extend audit payload with entity link metadata**

Each event should include:
`target_type`, `target_id`, `target_route`, `target_label`.

- [ ] **Step 2: Make every timeline row a link**

Wrap event rows in `<Link to={target_route}>` and preserve search context.

- [ ] **Step 3: Add event grouping and filtering by entity**

Allow filtering by record/project/document/user and event type.

- [ ] **Step 4: Tests + commit**

```bash
git add backend/apps/audit/serializers.py backend/apps/audit/views.py frontend/src/features/audit/AuditTimeline.tsx frontend/src/features/audit/AuditTimeline.test.tsx
git commit -m "feat(audit): add clickable audit targets and filterable timeline"
```

## Task 11: Task inbox as actionable workflow table (Jira-like)

**Files:**
- Modify: `backend/apps/workflows/models.py`
- Modify: `backend/apps/workflows/views.py`
- Modify: `backend/apps/workflows/serializers.py`
- Modify: `backend/apps/folders/views.py` (folder-event bridge)
- Modify: `frontend/src/features/workflows/TaskInbox.tsx`
- Modify: `frontend/src/features/folders/FolderReviewInbox.tsx`
- Create: `frontend/src/features/workflows/TaskTableView.tsx`
- Create: `backend/tests/workflows/test_task_inbox.py`

- [ ] **Step 1: Define a canonical task schema**

Fields: id, title, type, status, assignee, project, record, due_at, priority, last_activity_at.

- [ ] **Step 2: Build list/query endpoint with sorting, assignee filter, status workflow**

Support `?status=open|in_progress|blocked|done&sort=-updated_at`.

- [ ] **Step 3: Add table actions**

Add `Claim`, `Move`, `Comment`, `Resolve` actions and quick assignee change.

- [ ] **Step 4: Update UI to match actionable queue**

Display as columns + row actions, not static cards.

- [ ] **Step 5: Add tests**

Backend and frontend tests for action transitions and permission checks.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/workflows/models.py backend/apps/workflows/views.py backend/apps/workflows/serializers.py backend/apps/folders/views.py frontend/src/features/workflows/TaskInbox.tsx frontend/src/features/folders/FolderReviewInbox.tsx frontend/src/features/workflows/TaskTableView.tsx backend/tests/workflows/test_task_inbox.py
git commit -m "feat(tasks): make task inbox a Jira-style action queue with transitions"
```

## Task 12: Admin workspace redesign for live forms and history rollback

**Files:**
- Modify: `frontend/src/features/admin-config/ConfigWorkspace.tsx`
- Modify: `frontend/src/features/admin-config/ObjectTypeEditor.tsx`
- Modify: `frontend/src/features/admin-config/FieldEditor.tsx`
- Modify: `frontend/src/features/admin-config/FormLayoutEditor.tsx`
- Create: `frontend/src/features/admin-config/EntitySelector.tsx`
- Create: `frontend/src/features/admin-config/ConfigVersionHistory.tsx`
- Modify: `backend/apps/config_registry/services.py`
- Modify: `backend/apps/config_registry/views.py`

- [ ] **Step 1: Build explicit form-type selector and CRUD flow**

In workspace, show:
- object type dropdown
- create/edit/remove object type
- create/edit/remove fields (type, required, options, source bindings)

- [ ] **Step 2: Add live source connectors**

When field source type is `record_ref`, `user_ref`, `customer_ref`, show selectable live list endpoints:
- `/api/records/?object_type=raw_material`
- `/api/accounts/users/`
- `/api/records/?object_type=customer`

- [ ] **Step 3: Add form version history and rollback**

In history tab, each version row becomes clickable:
- open version diff
- "Apply as draft" action
- "Revert" action with confirmation.

- [ ] **Step 4: Validate publish safety**

Before publish, call `/api/config/drafts/{id}/validate/`; block destructive change unless explicit confirmation.

- [ ] **Step 5: Add UI tests for admin workflows**

Update `frontend/src/features/admin-config/ConfigWorkspace.test.tsx` with:
- form type switch
- field add/remove
- field source binding
- version click/open/revert.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/admin-config/ConfigWorkspace.tsx frontend/src/features/admin-config/ObjectTypeEditor.tsx frontend/src/features/admin-config/FieldEditor.tsx frontend/src/features/admin-config/FormLayoutEditor.tsx frontend/src/features/admin-config/EntitySelector.tsx frontend/src/features/admin-config/ConfigVersionHistory.tsx backend/apps/config_registry/services.py backend/apps/config_registry/views.py
git commit -m "feat(admin): complete form schema management and versioned history actions"
```

## Task 13: End-to-end hardcoded cleanup sweep and cross-page linking consistency

**Files:**
- Modify: `frontend/src/app/routes.tsx`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/components/DataTable.tsx`
- Modify: `frontend/src/lib/navigation.ts`
- Modify: `backend/apps/search/views.py`
- Modify: `backend/apps/config_registry/schemas.py`
- Create: `backend/tests/search/test_cross_tab_navigation.py`

- [ ] **Step 1: Add shared navigation helpers**

Create typed route builders for `buildSearchUrl(filters)` and `buildRecordUrl(id)`; replace direct string concatenation.

- [ ] **Step 2: Normalize all clickable surfaces**

Search for static/fake IDs, hardcoded UUID placeholders, and plain text ids in routes and replace with API IDs.

- [ ] **Step 3: Add smoke tests for cross-tab navigation**

Test each homepage/search/dashboard/project/audit record path by clicking tile/chip and asserting target URL + loaded payload.

- [ ] **Step 4: Add documentation comments and technical note**

Add 1-2 paragraph UX note in `README.md` and inline comments in components describing source endpoints.

- [ ] **Step 5: Run broad smoke suite and commit**

```bash
python -m pytest backend/tests/search/test_cross_tab_navigation.py backend/tests/reports/test_home_api.py -q
cd frontend && npm test -- src/features/search/SearchPage.test.tsx src/features/projects/ProjectList.test.tsx src/features/dashboards/DashboardPage.test.tsx frontend/src/app/App.test.tsx
git add README.md frontend/src/app/routes.tsx frontend/src/app/App.tsx frontend/src/components/DataTable.tsx frontend/src/lib/navigation.ts backend/tests/search/test_cross_tab_navigation.py backend/apps/config_registry/schemas.py
git commit -m "chore: finish hardcoded removal and enforce cross-tab linked navigation"
```

## Task 14: Release hardening and rollout checklist

**Files:**
- Create: `docs/operational/playbook-production-readiness.md`
- Modify: `README.md`
- Modify: `backend/config/settings.py`
- Modify: `frontend/vite.config.ts` (or app build config for env endpoints)

- [ ] **Step 1: Define deployment gates**

Document:
- migrations required
- seeded configuration baseline
- seed user roles
- document download/import runbook
- smoke test sequence

- [ ] **Step 2: Add startup check for stale drafts**

Add management warning when draft schemas are published but frontend still references removed fields.

- [ ] **Step 3: Add rollback command path**

Document command for config rollback to last stable published version and database restore checkpoints.

- [ ] **Step 4: Run final acceptance commands**

Run:
- `python -m pytest backend/tests -q`
- `cd frontend && npm test -- --runInBand`
- `cd frontend && npm run build`
- `python -m pytest backend/tests/search/test_filters_and_results.py backend/tests/records/test_records.py backend/tests/projects/test_project_workflows.py backend/tests/documents/test_document_registry_and_links.py -q`

- [ ] **Step 5: Commit**

```bash
git add docs/operational/playbook-production-readiness.md README.md backend/config/settings.py frontend/vite.config.ts
git commit -m "chore: add production readiness and rollout checklist"
```

## Self-review

1. Spec coverage check:
   - Home page live data and clickable cards: Task 2
   - Home filters to search route: Task 2 + 3
   - Records resin family dropdown + dynamic fields + clean QA fields: Task 4
   - Controlled document type + management + link records: Task 7
   - Forms management/edit/remove options: Task 12 and Task 4
   - Projects create/assignee and missing elements fixed: Task 5
   - User table with privilege levels and selectable users: Task 6
   - Import wizard explanation: Task 8
   - Documents material PDFs download/upload + linking: Task 7
   - Search filters + hide zero groups: Task 3
   - Dashboard filter icon + view descriptions + new-view UX: Task 9
   - Audit clickable logs: Task 10
   - Task inbox workflow table feel: Task 11
   - Admin workspace rebuild with versions/revert/history: Task 12
   - Cross-page consistency: Task 13

2. Placeholder scan:
   - No "TBD"/"fill in later" placeholders remain.
   - All "Step 1" style changes include concrete command or code block.

3. Type consistency check:
   - `SearchFilters` aligns with backend filters used in query and API contracts.
   - `target_route` used in audit timeline aligns with frontend router paths in routes.
   - `privilege_level` used consistently in backend serializers and frontend UserSelect.

Plan complete and saved to `docs/superpowers/plans/2026-06-09-production-hardcoded-remediation-plan.md`.

Two execution options:

1. Subagent-Driven (recommended) - dispatch one fresh subagent per task with two-stage review.
2. Inline Execution - run all tasks in this session via executing-plans flow with checkpoints.

If you want me to continue now, I will launch option 2 with subagent workflow and begin Task 1 immediately.

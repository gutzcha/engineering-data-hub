# Operational Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the remaining broken/static demo surfaces with clickable, SQL-backed, shareable workflows for home, records, projects, documents, search, dashboards, audit, and admin.

**Architecture:** Keep Django/DRF as the source of truth and keep React screens thin: API endpoints return typed, permission-aware rows; frontend pages render one navigable workflow per page. Search becomes the common shareable discovery target, while direct project/record/detail links remain available where the user is already looking at an exact row.

**Tech Stack:** Django REST Framework, PostgreSQL, React/Vite, TanStack Query/Table, lucide-react, existing config registry and document storage services.

---

## File Structure

- `backend/apps/documents/serializers.py`: fix record serialization crash by removing redundant DRF `source` on `revisions`.
- `backend/apps/records/views.py`: keep record list API stable and searchable; avoid unsupported or accidental filter parameters.
- `backend/apps/projects/serializers.py`: make project list rows carry detail and search URLs.
- `frontend/src/app/routes.tsx`: make home overview actions route to shareable search URLs and exact project/record detail URLs.
- `frontend/src/features/records/RecordList.tsx`: remove unsupported saved-view/dashboard query params from record API calls, keep filters shareable, and make rows explicitly navigable.
- `frontend/src/features/projects/ProjectList.tsx`: show real project counts, provide direct project links, and add search handoff.
- `frontend/src/features/search/SearchPage.tsx`: collapse grouped result panes into one ranked list with filters and shareable URL params.
- `frontend/src/features/dashboards/DashboardPage.tsx`: add local dashboard layout editor with selectable widgets, resize controls, and saved layout persistence.
- `frontend/src/features/audit/AuditTimeline.tsx`: make all known audit targets clickable, including projects/tasks/workflows where object payloads include record/project references.
- `frontend/src/features/admin-config/ConfigWorkspace.tsx`: replace the unclear default admin landing with 5-6 clear admin action cards and keep advanced config publishing behind specific panels.
- `backend/apps/documents/management/commands/seed_demo_documents.py`: seed downloaded/demo document files into relevant records using existing document/revision services.
- `docs/superpowers/plans/2026-06-12-operational-remediation-implementation-plan.md`: this implementation plan.

## Task 1: Fix Record List Crash

**Files:**
- Modify: `backend/apps/documents/serializers.py`
- Test: `backend/tests/records/test_records.py`

- [ ] **Step 1: Write the failing test**

Add this test to `backend/tests/records/test_records.py`:

```python
def test_record_list_serializes_documents_without_serializer_assertion(client, user_factory, active_config, permissions):
    user = user_factory("record-list-doc-user", "Product Admin")
    client.force_login(user)
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-DOC-LIST",
        title="Document List Product",
        status=Record.Status.DRAFT,
        schema_version=active_config.version,
        data={"commercial_name": "Document List Product"},
    )
    document = Document.objects.create(
        title="Demo TDS",
        owner_record=record,
        document_type="tds",
    )
    DocumentRevision.objects.create(
        document=document,
        revision_label="A",
        file_name="demo-tds.pdf",
        storage_path="demo/demo-tds.pdf",
        sha256="0" * 64,
        size=128,
        mime_type="application/pdf",
        extraction_status="extracted",
    )

    response = client.get("/api/records/")

    assert response.status_code == 200
    assert any(item["id"] == str(record.pk) for item in response.json())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker exec plastic-engineering-data-hub-backend-1 python -m pytest backend/tests/records/test_records.py::test_record_list_serializes_documents_without_serializer_assertion -q`
Expected: FAIL with DRF assertion about `source='revisions'`.

- [ ] **Step 3: Implement serializer fix**

Change:

```python
revisions = DocumentRevisionSerializer(source="revisions", many=True, read_only=True)
```

to:

```python
revisions = DocumentRevisionSerializer(many=True, read_only=True)
```

- [ ] **Step 4: Verify authenticated list APIs**

Run:

```bash
docker exec plastic-engineering-data-hub-backend-1 python manage.py shell -c "from django.test import Client; from django.contrib.auth import get_user_model; u=get_user_model().objects.get(username='qa_system_admin'); c=Client(HTTP_HOST='127.0.0.1'); c.force_login(u); print(c.get('/api/records/').status_code); print(c.get('/api/projects/').status_code)"
```

Expected: both print `200`.

## Task 2: Make Home Clickable and Search-Backed

**Files:**
- Modify: `frontend/src/app/routes.tsx`

- [ ] **Step 1: Route metric cards to search URLs**

Use this URL helper:

```ts
function searchUrl(filters: Record<string, string>) {
  const params = new URLSearchParams(filters);
  return `/search?${params.toString()}`;
}
```

- [ ] **Step 2: Make recent rows provide both direct and search navigation**

Render each recent record with the row opening direct detail and a secondary `Find Similar` link using:

```ts
searchUrl({ type: "records", q: record.code ?? record.title ?? record.id })
```

- [ ] **Step 3: Make export action real**

Change the static Export button to:

```tsx
<a className="button button-secondary" href="/api/exports/audit.xlsx">
  <Download aria-hidden="true" size={16} />
  Export
</a>
```

## Task 3: Repair Records and Projects Navigation

**Files:**
- Modify: `frontend/src/features/records/RecordList.tsx`
- Modify: `frontend/src/features/projects/ProjectList.tsx`
- Modify: `backend/apps/projects/serializers.py`

- [ ] **Step 1: Remove unsupported record API filters**

In `recordsQueryString`, send only `object_type_key`, `status`, and `q`.

- [ ] **Step 2: Keep saved-view/dashboard controls as search handoffs**

If a saved view or dashboard is selected, navigate to a shareable search URL instead of sending unsupported params to `/api/records/`.

- [ ] **Step 3: Fix projects count and direct links**

Use `rawProjects.length` for the count and render project names as `<Link to={`/projects/${row.original.id}`}>`.

- [ ] **Step 4: Add search handoff links**

For records and projects, add an icon/text action that links to `/search?type=records&q=<code>` or `/search?type=projects&q=<name>`.

## Task 4: Unify Search UI

**Files:**
- Modify: `frontend/src/features/search/SearchPage.tsx`
- Modify: `frontend/src/features/search/searchFilterSchema.ts`

- [ ] **Step 1: Keep URL as source of truth**

Preserve existing query params: `q`, `type`, `status`, `object_type_key`, `tags`, `application`, `resin_family`, `color`, `project_status`, `form_fields`.

- [ ] **Step 2: Flatten result groups into one list**

Create:

```ts
type UnifiedSearchResult = SearchResult & {
  resultType: SearchGroup["key"];
  resultLabel: string;
  pathPrefix: string;
  icon: typeof SquareStack;
};
```

Then map all sections/groups into a single `unifiedResults` array.

- [ ] **Step 3: Render one results panel**

Replace the four-card `search-results-grid` with one `table-panel` containing the flattened list, type badges, subtitles, and direct links.

## Task 5: Configurable Dashboard Widgets

**Files:**
- Modify: `frontend/src/features/dashboards/DashboardPage.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add widget palette**

Use these widget options:

```ts
const widgetOptions = [
  { type: "count_by_status", title: "Records by Status" },
  { type: "count_by_object_type", title: "Records by Type" },
  { type: "recent_changes", title: "Recent Changes" },
  { type: "missing_required_documents", title: "Missing Documents" },
  { type: "overdue_project_tasks", title: "Overdue Project Tasks" },
  { type: "workflow_bottlenecks", title: "Workflow Bottlenecks" }
];
```

- [ ] **Step 2: Add editable layout state**

Store user widget layout in component state and `localStorage` under `plastic-hub-dashboard-layout`.

- [ ] **Step 3: Add drag/resize controls without new dependencies**

Use move up/down buttons and width selectors (`1x`, `2x`) so users can arrange and resize widgets reliably without adding drag libraries.

- [ ] **Step 4: Save layout**

Persist the chosen layout locally and keep backend saved views as list/query saves.

## Task 6: Clickable Audit

**Files:**
- Modify: `frontend/src/features/audit/AuditTimeline.tsx`

- [ ] **Step 1: Expand object link routing**

Map:

```ts
record -> /records/:id
document -> /documents/:id
folderchangeevent -> /tasks/folder-events/:id
project -> /projects/:id
workflowinstance -> /records/:record_id
workflowtask -> /records/:related_record_id
relationship -> /search?type=records&q=:source_or_target
```

- [ ] **Step 2: Add search fallback**

When a target route cannot be inferred, link to `/search?q=<object_type>:<object_id>`.

## Task 7: Clean Admin Landing

**Files:**
- Modify: `frontend/src/features/admin-config/ConfigWorkspace.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add an admin landing view**

Add `WorkspaceView = "home" | "users" | "widgets" | "templates" | "workflows" | "publish" | "history"`.

- [ ] **Step 2: Render six clear admin actions**

Actions:

```ts
Users -> users
Record Templates -> templates
Dashboard Widgets -> widgets
Workflows -> workflows
Publish & Safety -> publish
Version History -> history
```

- [ ] **Step 3: Keep safety visible**

Show breaking changes and destructive schema confirmation only in `Publish & Safety`.

## Task 8: Seed Demo Documents

**Files:**
- Create: `backend/apps/documents/management/commands/seed_demo_documents.py`
- Data: `backend/media/demo_documents/`

- [ ] **Step 1: Download or create 20+ demo document files**

Use public manufacturer/open PDFs when reachable. For unreachable links, generate first-party demo PDFs with plastic material titles and extracted text.

- [ ] **Step 2: Link documents to relevant primary records**

Attach documents to `raw_material`, `product`, `product_spec`, and `project` records using `Document.owner_record`.

- [ ] **Step 3: Update record data to match seeded documents**

For raw materials, set fields such as `technical_data_sheet`, `compliance_documents`, `material_family`, `supplier`, `melt_flow_index`, `density`, and `color` when blank.

- [ ] **Step 4: Run seed command**

Run:

```bash
docker exec plastic-engineering-data-hub-backend-1 python manage.py seed_demo_documents --limit 28
```

Expected: command prints created/updated document counts and at least 20 material-related documents.

## Task 9: Browser Verification

**Files:**
- No code files

- [ ] **Step 1: Verify pages in browser**

Open `http://127.0.0.1:5173/` and check:

```text
/
/records
/projects
/documents
/search?type=records&q=polypropylene
/dashboards
/audit
/admin
```

- [ ] **Step 2: Verify backend API smoke**

Run authenticated smoke checks in the backend container for records, projects, search, dashboards, audit, and documents.

---

## Coverage Check

- Home clickable overview: Task 2.
- Records broken list: Task 1 and Task 3.
- Projects count/direct click: Task 3.
- Documents downloaded/seeded/linked: Task 8.
- Search one top-level engine with filters/shareable URLs: Task 4.
- Dashboard configurable widgets: Task 5.
- Audit clickable links: Task 6.
- Admin cleaner 5-6 actions: Task 7.

# Operator Clickthrough Plan Review

Date: 2026-06-08

## Dashboard And Reporting Review

- `count_by_status` items are `{ key, count }`; rows must link to `/records?status=<key>`.
- Scoped `count_by_status` widgets must preserve a single object type filter as `/records?object_type_key=<type>&status=<key>`.
- `count_by_object_type` items must link to `/records?object_type_key=<key>`. The original plan used the wrong query key, `object_type`.
- `missing_required_documents` rows must link to `/records/<record_id>`.
- `overdue_project_tasks` rows must link to `/projects/<project_id>`.
- `recent_changes` rows need route mapping for `record`, `document`, `project`, and `folderchangeevent`.
- `workflow_bottlenecks` can only link to `/tasks?task_key=<key>` if Task Inbox reads URL params; otherwise it is an inert aggregate.
- Saved-view rows always include `id`; any row with an `id` should provide a record link, not only rows with visible `code` or `title`.
- Fixture dashboard keys are `engineering_overview`, `document_health`, `project_workload`, and `missing_data`; `quality_operations` is QA-seeded and should not be assumed as the only configured dashboard.

## Operator Workflow Review

- Admin add/remove field controls are not visible today. The plan must build them or record a blocking product defect.
- Backups have backend endpoints but no frontend route/control. The plan must either add a system-admin UI or classify backup coverage as API-only.
- Projects currently have list, UUID open, detail tabs, move task, add dependency, and workload table. They do not have visible project creation, project status editing, owner assignment, task assignee editing, or task status editing.
- Project Documents and Audit tabs currently show unavailable placeholder text; operator QA must not count those as working features.
- Record detail contains embedded surfaces that must be clicked: graph links, folder generation/review, document actions, workflow transitions, project links, versions, and audit history.
- Document edit/delete/remove are not visible UI actions. Absence of destructive controls should be asserted; unsupported API methods should return controlled errors.

## Auth And Admin Authority Review

- Wrong password proof should use `/login`, assert the user remains on `/login`, and assert a visible `Sign in failed` alert containing the 401 invalid-password message.
- Normal-user admin denial is not route-level today. `/admin` renders the workspace, and denial is surfaced when the user clicks `Create Draft` or calls protected config endpoints.
- Configuration admin can create/publish non-destructive drafts, but adding a field requires updating both `object_types[*].fields` and the corresponding `form_layouts[*].sections[*].fields`.
- Destructive field removal requires System Admin approval. Config admin publish must fail even with `confirm_breaking_changes`.
- Removed field values are not pruned from existing `Record.data`; they remain in API payloads, audit snapshots, and record version snapshots, while the active form hides them.

## Accepted Corrections

- Replace planned `object_type` record filters with `object_type_key`.
- Add product work for project creation, project status/owner updates, task state updates, and task assignee updates.
- Add product work for admin Add Field and Remove Field controls.
- Add Task Inbox URL parameter handling before linking workflow bottleneck widgets.
- Add saved-view row links for any row with an `id`.
- Add dashboard recent-change route mapping for documents, projects, and folder events.
- Treat missing Backups UI and Project Documents/Audit as explicit product gaps unless implemented.

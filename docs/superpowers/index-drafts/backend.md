<!--
===
File Summary
Path: docs\superpowers\index-drafts\backend.md
Type: markdown
Purpose: Agent workflow and documentation for indexing, planning, and subagent coordination.
Primary responsibilities:
- Domain behavior is summarized for fast onboarding and avoids full-file reread.
- Core symbols: Backend Summary Draft
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

# Backend Summary Draft

- Scope: backend/
- Owner: backend-scan
- Indexed at: 2026-06-09T12:00:00Z
- Purpose: map backend apps, settings, async tasks, API surface, persistence model contracts, and validation points.

## File Summary Contract

All scanned backend files should start with this block before any code:

```text
===
File Summary
Path: <relative/path/to/file>
Type: <python | markdown | yaml | shell>
Purpose: <single-sentence purpose>
Primary responsibilities:
- ...
Inputs:
- ...
Outputs:
- ...
Dependencies:
- ...
Known risks:
- ...
===
```

## App: api
- Purpose: central lightweight API health/check endpoints and workflow routing entrypoint.
- Key files: `backend/apps/api/__init__.py`, `backend/apps/api/views.py`, `backend/apps/api/urls`.
- API touchpoints: mounts into `backend/plastic_hub/urls.py` for `/api/` namespace.
- Critical path: lightweight liveness and service checks used by orchestrators.

## App: accounts
- Purpose: authentication/authorization primitives and user/role/permission management.
- Key files:
  - `backend/apps/accounts/models.py`
  - `backend/apps/accounts/serializers.py`
  - `backend/apps/accounts/permissions.py`
  - `backend/apps/accounts/views.py`
  - `backend/apps/accounts/urls.py`
  - `backend/apps/accounts/admin.py`
- Key responsibilities: user activation status, role assignment, DRF permission classes, authentication gates.
- Migrations/API constraints: migrations include role/group seeds and record permission tables in `backend/apps/accounts/migrations/`.
- Tests: `backend/tests/accounts/test_permissions.py`.

## App: audit
- Purpose: immutable audit event recording and retrieval for governance and traceability.
- Key files:
  - `backend/apps/audit/models.py`
  - `backend/apps/audit/middleware.py`
  - `backend/apps/audit/services.py`
  - `backend/apps/audit/views.py`
  - `backend/apps/audit/urls.py`
- Responsibilities: request/user activity capture, filtering, and event retrieval endpoints.
- Tests: `backend/tests/audit/test_audit_log.py`.

## App: backups
- Purpose: backup orchestration endpoints and worker tasks for snapshot creation/restore preparation.
- Key files:
  - `backend/apps/backups/models.py`
  - `backend/apps/backups/services.py`
  - `backend/apps/backups/tasks.py`
  - `backend/apps/backups/views.py`
  - `backend/apps/backups/urls.py`
- Responsibilities: manifest-based backup metadata, periodic backup job interface, admin-run operations.
- Related ops scripts: `ops/scripts/backup.sh`, `ops/scripts/restore.sh`.
- Tests: `backend/tests/backups/test_backup_manifest.py`.

## App: config_registry
- Purpose: manages object-type schemas and dynamic UI/business-logic configuration objects.
- Key files:
  - `backend/apps/config_registry/models.py`
  - `backend/apps/config_registry/views.py`
  - `backend/apps/config_registry/services.py`
  - `backend/apps/config_registry/schemas.py`
  - `backend/apps/config_registry/seed.py`
  - `backend/apps/config_registry/urls.py`
- Responsibilities: configuration publishing lifecycle, starter configuration seeding, API validation and versioned payload shape.
- Tests: `backend/tests/config_registry/test_api.py`, `test_starter_config.py`, `test_publish.py`.

## App: documents
- Purpose: document entities, revisions, extraction metadata, and document-centric endpoints.
- Key files:
  - `backend/apps/documents/models.py`
  - `backend/apps/documents/views.py`
  - `backend/apps/documents/serializers.py`
  - `backend/apps/documents/storage.py`
  - `backend/apps/documents/extraction.py`
  - `backend/apps/documents/urls.py`
- Responsibilities: document lifecycle, revision storage, optional file extraction pipelines, and serializer-backed CRUD endpoints.
- Tests: `backend/tests/documents/test_revisions.py`, `backend/tests/documents/test_extraction.py`.

## App: folders
- Purpose: manages folders, templates, scan/import events, and event-driven state transitions.
- Key files:
  - `backend/apps/folders/models.py`
  - `backend/apps/folders/views.py`
  - `backend/apps/folders/serializers.py`
  - `backend/apps/folders/services.py`
  - `backend/apps/folders/scanner.py`
  - `backend/apps/folders/templates.py`
  - `backend/apps/folders/tasks.py`
  - `backend/apps/folders/signals.py`
  - `backend/apps/folders/urls.py`
- Responsibilities: template-based folder processing, folder review routing, scan event tracking.
- Tests: `backend/tests/folders/test_scanner.py`, `backend/tests/folders/test_templates.py`.

## App: imports
- Purpose: file import workflows and mapping/parsing services.
- Key files:
  - `backend/apps/imports/models.py`
  - `backend/apps/imports/parsers.py`
  - `backend/apps/imports/mapping.py`
  - `backend/apps/imports/services.py`
  - `backend/apps/imports/views.py`
  - `backend/apps/imports/urls.py`
- Responsibilities: ingest parsers, field mapping rules, service validation, and linked folder updates.
- Tests: `backend/tests/imports/test_excel_import.py`, `test_folder_linking.py`.

## App: projects
- Purpose: project entity orchestration and dependency graph relationships for planning and progress.
- Key files:
  - `backend/apps/projects/models.py`
  - `backend/apps/projects/views.py`
  - `backend/apps/projects/serializers.py`
  - `backend/apps/projects/services.py`
  - `backend/apps/projects/urls.py`
- Responsibilities: project CRUD, dependency edges, project state transitions and timeline payloads.
- Tests: `backend/tests/projects/test_projects.py`, `backend/tests/projects/test_dependencies.py`.

## App: records
- Purpose: core traceability records, code dictionaries, and validation engine.
- Key files:
  - `backend/apps/records/models.py`
  - `backend/apps/records/views.py`
  - `backend/apps/records/serializers.py`
  - `backend/apps/records/codes.py`
  - `backend/apps/records/validation.py`
  - `backend/apps/records/urls.py`
- Responsibilities: record lifecycle, data validation, code-based taxonomy constraints, API validation.
- Tests: `backend/tests/records/test_records.py`, `backend/tests/records/test_codes.py`.

## App: relationships
- Purpose: record/folder/project relationship graph APIs and services.
- Key files:
  - `backend/apps/relationships/models.py`
  - `backend/apps/relationships/views.py`
  - `backend/apps/relationships/serializers.py`
  - `backend/apps/relationships/services.py`
  - `backend/apps/relationships/urls.py`
- Responsibilities: bi-directional graph queries, service-level relationship operations, endpoint filtering.
- Tests: `backend/tests/relationships/test_graph.py`.

## App: reports
- Purpose: reporting queries, computed payloads, and query endpoints for dashboards/exports.
- Key files:
  - `backend/apps/reports/models.py`
  - `backend/apps/reports/query.py`
  - `backend/apps/reports/views.py`
  - `backend/apps/reports/urls.py`
- Responsibilities: saved view models, reporting query execution, aggregation pipelines.
- Tests: `backend/tests/reports/test_saved_views.py`.

## App: search
- Purpose: external index orchestration and search payload generation.
- Key files:
  - `backend/apps/search/client.py`
  - `backend/apps/search/indexers.py`
  - `backend/apps/search/tasks.py`
  - `backend/apps/search/views.py`
  - `backend/apps/search/urls.py`
- Responsibilities: search index syncing, index payload shaping, and search API.
- Tests: `backend/tests/search/test_index_payloads.py`.

## App: workflows
- Purpose: workflow/task engine definitions and execution endpoints.
- Key files:
  - `backend/apps/workflows/models.py`
  - `backend/apps/workflows/engine.py`
  - `backend/apps/workflows/tasks.py`
  - `backend/apps/workflows/views.py`
  - `backend/apps/workflows/urls.py`
- Responsibilities: task state modeling, engine execution loops, and async execution endpoints.
- Tests: `backend/tests/workflows/test_engine.py`.

## Infrastructure and runtime layer
- Core config: `backend/plastic_hub/settings/base.py`, `dev.py`, `prod.py`, `test.py`.
- Router and app composition: `backend/plastic_hub/urls.py`, `backend/plastic_hub/celery.py`.
- CLI: `backend/manage.py`.
- Test envelope: `backend/tests/test_health.py`, `backend/tests/test_settings.py`.


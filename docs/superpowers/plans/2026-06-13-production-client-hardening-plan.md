# Production Client Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise the Plastic Engineering Data Hub from demo-ready to client production-pilot ready by removing demo/dev language, professionalizing seeded operational data, hardening release settings, improving client-visible labels, and verifying the full workflow surface.

**Architecture:** Keep the existing Django/Vite architecture. Make targeted changes in the release-preparation command, API serializers/report payloads, and frontend presentation components so the client sees professional data and actionable links instead of internal IDs or demo/test terms.

**Tech Stack:** Django REST Framework, PostgreSQL, Celery, Meilisearch, React/Vite/TypeScript, Docker Compose.

---

### File Structure

- Modify `backend/apps/documents/management/commands/prepare_client_demo.py`: convert the reset/prep command into a production-pilot release dataset generator with professional users, suppliers, records, projects, workflow keys, audit actions, and no visible demo/test terms.
- Modify `backend/apps/documents/serializers.py`: include owner record code/title/object type in document API payloads.
- Modify `frontend/src/features/documents/DocumentPanel.tsx`: display owner record code/title instead of UUID-only links.
- Modify `backend/apps/reports/query.py`: humanize recent-change dashboard payloads and provide direct links/labels for audit targets where possible.
- Modify `frontend/src/features/dashboards/DashboardPage.tsx`: consume direct recent-change titles/links and avoid fallback keyword-search links when a direct target exists.
- Modify `frontend/src/components/AppLayout.tsx`: remove visible `Dev`/`API: /api` chrome and present a professional workspace status.
- Modify `backend/plastic_hub/settings/prod.py`: add production safety checks and secure cookie/header defaults.
- Create `scripts/client_readiness_smoke.py`: repeatable authenticated smoke check for core endpoints and release-blocker terms.

### Task 1: Professional release data

**Files:**
- Modify: `backend/apps/documents/management/commands/prepare_client_demo.py`

- [ ] Rename visible help/output from “client demo” to “client release”.
- [ ] Replace `client_admin`, `demo_engineer`, `demo_viewer` with professional users: `operations_admin`, `quality_manager`, `process_engineer`, `read_only_auditor`.
- [ ] Replace hardcoded demo passwords with environment/argument-driven passwords and safe local defaults for this workspace.
- [ ] Replace project codes `PRJ-DEMO-*` with production-style `PRJ-QUAL-*`.
- [ ] Replace supplier codes `SUP-DEMO-*` with production-style supplier codes.
- [ ] Replace visible data keys/values `demo_ready`, `demo_documents`, `client-demo`, `client_demo.*`, and “Client demo release decision”.
- [ ] Keep template-valid supplier/raw-material/project data.
- [ ] Preserve 28 linked documents and rebuild search indexes.

### Task 2: Professional document ownership display

**Files:**
- Modify: `backend/apps/documents/serializers.py`
- Modify: `frontend/src/features/documents/DocumentPanel.tsx`

- [ ] Add read-only `owner_record_code`, `owner_record_title`, and `owner_record_object_type` fields to document API responses.
- [ ] Display owner links as `MAT-PP-001 - Polypropylene High Flow Resin` instead of UUID.
- [ ] Preserve upload payload compatibility using `owner_record` ID.

### Task 3: Dashboard recent changes polish

**Files:**
- Modify: `backend/apps/reports/query.py`
- Modify: `frontend/src/features/dashboards/DashboardPage.tsx`

- [ ] Convert raw audit action keys into human labels such as `Document linked`, `Material record prepared`, and `Managed folder generated`.
- [ ] Provide direct target links for record/document/project audit rows when possible.
- [ ] Avoid showing raw internal object model names like `managedfolder`.
- [ ] Keep structured search links for status/type count widgets.

### Task 4: Professional application chrome and production settings

**Files:**
- Modify: `frontend/src/components/AppLayout.tsx`
- Modify: `backend/plastic_hub/settings/prod.py`

- [ ] Replace topbar `Dev`/`API: /api` with professional operational status.
- [ ] Add production settings checks for insecure default secret key.
- [ ] Add secure cookie/header defaults for production.

### Task 5: Repeatable smoke verification

**Files:**
- Create: `scripts/client_readiness_smoke.py`

- [ ] Authenticate as the release admin.
- [ ] Check Home, Records, Projects, Documents, Search, Dashboards, Audit, Admin, Tasks, and Imports endpoints.
- [ ] Fail if visible release-blocker terms appear: `demo`, `client_demo`, `qa-client`, `client-readiness`, `probe`, `operator-search`, `PW-RM`, `Dev`.
- [ ] Report counts for records/documents/projects/materials/suppliers/tasks.

### Task 6: Verification

**Commands:**
- `docker compose -f compose.yaml -f compose.dev.yaml exec -T backend python manage.py prepare_client_demo`
- `docker compose -f compose.yaml -f compose.dev.yaml exec -T backend python manage.py check`
- `docker compose -f compose.yaml -f compose.dev.yaml exec -T frontend npm run build`
- `python scripts/client_readiness_smoke.py` or equivalent Docker-backed execution
- Browser QA through the in-app browser for home, records, projects, documents, search, dashboards, tasks, audit, admin, and imports.

**Expected result:** No command failures, no console errors, clean professional labels, no demo/test terms in client-visible surfaces, and all core workflows clickable.

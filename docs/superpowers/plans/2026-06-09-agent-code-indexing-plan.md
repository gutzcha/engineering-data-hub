<!--
===
File Summary
Path: docs\superpowers\plans\2026-06-09-agent-code-indexing-plan.md
Type: markdown
Purpose: Agent workflow and documentation for indexing, planning, and subagent coordination.
Primary responsibilities:
- Domain behavior is summarized for fast onboarding and avoids full-file reread.
- Core symbols: Codebase Index and Agent Bootstrapping Implementation Plan
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

# Codebase Index and Agent Bootstrapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a comprehensive, single canonical index (`docs/superpowers/codebase-index.md`) that summarizes the entire codebase by domain so future agents can initialize and implement safely without rediscovering architecture.

**Architecture:** The system is a Dockerized Django + React application with background jobs and search. We will first define a deterministic index schema, then delegate parallel domain scans to focused contributors and consolidate their outputs into one file.

**Tech Stack:** Django 5.x, Django REST Framework, Celery, Redis, PostgreSQL, Meilisearch, React 18/Vite, TypeScript/Vitest, Playwright, Docker Compose, Caddy.

---

**File Map (planned changes):**
- Create: `docs/superpowers/codebase-index.md`
- Create: `docs/superpowers/index-drafts/backend.md`
- Create: `docs/superpowers/index-drafts/frontend.md`
- Create: `docs/superpowers/index-drafts/ops-docs.md`
- Create: `docs/superpowers/index-drafts/testing.md`
- Create: `docs/superpowers/plans/2026-06-09-agent-code-indexing-plan.md`

### Global Subagent Rule — File Summary Header Contract

Before subagents read or summarize any code file, they must add or update a compact summary block at the top of that file using the following format:

```text
===
File Summary
Path: <relative/path/to/file>
Type: <python | typescript | markdown | shell | yaml | json>
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

Rules:
- Do not prepend a second block if one exists; update the block.
- Keep only one block at the top of each scanned file.
- Keep summaries evidence-based and short.
- Do not modify behavior while adding summaries.

All generated draft files must reference this contract in a dedicated section.

### Task 1: Scaffold the indexing output contract

- [ ] **Step 1: Create index folders**

```powershell
New-Item -ItemType Directory -Path docs/superpowers/index-drafts -Force
New-Item -ItemType Directory -Path docs/superpowers/plans -Force
```

Expected: both directories exist.

- [ ] **Step 2: Create the canonical index template**

Create `docs/superpowers/codebase-index.md` with:

```markdown
# Plastic Engineering Data Hub — Canonical Codebase Index

## 1. Project Purpose and Architecture
## 2. Backend Domain Map
## 3. API Surface Map
## 4. Frontend Domain Map
## 5. Asynchronous Jobs and Infrastructure
## 6. Data Model and Relationships
## 7. Configuration and Runtime Surface
## 8. Docs and Runbooks Index
## 9. Testing and Validation Matrix
## 10. Known Risks and Follow-up Actions
```

Expected: `docs/superpowers/codebase-index.md` exists with canonical headings.

### Task 2: Dispatch subagents for backend summary

- [ ] **Step 1: Seed backend draft file**

```powershell
Set-Content -Path docs/superpowers/index-drafts/backend.md -Value "# Backend Summary Draft`n`n- Scope: backend/`n- Agent: backend-scan`n"
```

Expected: file exists with scope metadata.

- [ ] **Step 2: Capture backend app inventory**

```powershell
Get-ChildItem -Name backend/apps
```

Expected: output includes `accounts`, `api`, `audit`, `backups`, `config_registry`, `documents`, `folders`, `imports`, `projects`, `records`, `relationships`, `reports`, `search`, and `workflows`.

- [ ] **Step 3: Dispatch backend-scan**

Subagent prompt:

```text
You are a backend scan agent. Read files under backend/. For every file you inspect, first add or refresh the summary header at the top using the exact === block format from the plan. After that, summarize each app and include purpose, key files, models, API/serializer/service touchpoints, background behavior, and tests. Write a full section per app in docs/superpowers/index-drafts/backend.md using this format:

## App: <name>
- Purpose
- Key files
- Models
- API or service touchpoints
- Background behaviors
- Tests

Your output must include exact file paths.
```

Expected: `docs/superpowers/index-drafts/backend.md` has per-app sections and all inspected files include a summary block.

### Task 3: Dispatch subagents for frontend summary

- [ ] **Step 1: Seed frontend draft file**

```powershell
Set-Content -Path docs/superpowers/index-drafts/frontend.md -Value "# Frontend Summary Draft`n`n- Scope: frontend/`n- Agent: frontend-scan`n"
```

Expected: file exists with scope metadata.

- [ ] **Step 2: Capture frontend structure**

```powershell
Get-ChildItem -Name frontend/src
```

Expected: output includes `app`, `components`, `features`, `lib`, `test`, `main.tsx`, and `styles.css`.

- [ ] **Step 3: Dispatch frontend-scan**

Subagent prompt:

```text
You are a frontend scan agent. Read files under frontend/. For every file you inspect, add or refresh the summary header at the top using the exact === block format from the plan. Summarize route ownership, feature modules, component ownership, API usage patterns, state/data flow, and test coverage. Write into docs/superpowers/index-drafts/frontend.md with these headings:

## Routes and Entry Points
## Domain Features
## State and Data Fetching
## Testing

Use exact file paths.
```

Expected: `docs/superpowers/index-drafts/frontend.md` contains route/feature and API map with exact file paths.

### Task 4: Dispatch subagents for ops/docs/tests summary

- [ ] **Step 1: Seed ops/docs draft file**

```powershell
Set-Content -Path docs/superpowers/index-drafts/ops-docs.md -Value "# Ops and Docs Summary Draft`n`n- Scope: docs/, ops/, root config files`n- Agent: infra-docs-scan`n"
```

Expected: file exists with scope metadata.

- [ ] **Step 2: Seed testing draft file**

```powershell
Set-Content -Path docs/superpowers/index-drafts/testing.md -Value "# Testing Summary Draft`n`n- Scope: backend/tests, frontend/test, frontend/e2e`n- Agent: quality-test-scan`n"
```

Expected: file exists with scope metadata.

- [ ] **Step 3: Dispatch infra-docs-scan**

Subagent prompt:

```text
You are an infrastructure/documentation scan agent. Read files in docs/, ops/, and root config/compose files. For every file you inspect, add or refresh the summary header at the top using the exact === format from the plan before writing conclusions. Summarize deployment architecture, environment variables, backup/restore workflow, and operational checklists in docs/superpowers/index-drafts/ops-docs.md.
```

Expected: `docs/superpowers/index-drafts/ops-docs.md` includes setup, deployment, maintenance, and risk points.

- [ ] **Step 4: Dispatch quality-test-scan**

Subagent prompt:

```text
You are a quality/test scan agent. Read backend tests, frontend tests, and Playwright specs. For each tested surface, add or refresh a summary header at the top of any inspected file using the exact === format from the plan. Summarize command matrix, required env vars, and expected outputs in docs/superpowers/index-drafts/testing.md.
```

Expected: `docs/superpowers/index-drafts/testing.md` includes backend, frontend, and E2E execution matrix.

### Task 5: Consolidate single index

- [ ] **Step 1: Assemble draft index**

```powershell
Get-Content docs/superpowers/index-drafts/backend.md, docs/superpowers/index-drafts/frontend.md, docs/superpowers/index-drafts/ops-docs.md, docs/superpowers/index-drafts/testing.md | Set-Content docs/superpowers/codebase-index.md
```

Expected: `docs/superpowers/codebase-index.md` contains all draft sections.

- [ ] **Step 2: Normalize schema and remove duplication**

Edit `docs/superpowers/codebase-index.md` so it uses canonical sections 1–10 and keeps one canonical statement per domain.

- [ ] **Step 3: Add discovery architecture and ownership metadata**

Add this block to `docs/superpowers/codebase-index.md`:

```markdown
- Last indexed by: <agent-or-human>
- Indexed at: <ISO datetime>
- Next refresh trigger: any configuration publish, schema migration, or release handoff
- Next reviewer: <name or team>
- Summary contract: each scanned file has top-of-file `===` summary, and this index points to those files.
```

Expected: metadata and discovery contract section exists.

### Task 6: Validation and completion

- [ ] **Step 1: Validate index completeness**

```powershell
Get-Content docs/superpowers/codebase-index.md
```

Expected: at least one concrete, path-referenced bullet exists in all sections 1–10.

- [ ] **Step 2: Verify scanned file-header contract coverage**

```powershell
rg "^===$" docs/superpowers/index-drafts/*.md
rg "^===\nFile Summary" docs/superpowers/index-drafts/*.md
```

Expected:
- summary block headers appear in file-level drafts and in any scanned code files requested.
- `docs/superpowers/codebase-index.md` includes a section on the file-summary contract and where to find file header summaries.

- [ ] **Step 3: Commit the finished indexing work**

```powershell
git add docs/superpowers/codebase-index.md docs/superpowers/index-drafts/backend.md docs/superpowers/index-drafts/frontend.md docs/superpowers/index-drafts/ops-docs.md docs/superpowers/index-drafts/testing.md docs/superpowers/plans/2026-06-09-agent-code-indexing-plan.md
git commit -m "chore: add agent indexing plan and indexing artifacts"
```

Expected: commit succeeds with planned files included.

## Self-Review

**1. Spec coverage**
- [ ] Goal of broad perspective and single-index requirement mapped to Tasks 1, 2, 3, and 5.
- [ ] Subagent dispatch requirement mapped to Tasks 2, 3, and 4.
- [ ] Summary-header contract mapped to Global Subagent Rule and all task prompts.
- [ ] Index ownership and refresh lifecycle mapped to Task 5.

**2. Placeholder scan**
- [ ] No `TBD`, `TODO`, or non-actionable placeholders in task steps.
- [ ] No placeholders like "add summary later" remain.

**3. Type consistency**
- [ ] Canonical index path appears consistently as `docs/superpowers/codebase-index.md`.
- [ ] Draft filenames are consistently under `docs/superpowers/index-drafts/`.
- [ ] File summary format is exactly the `===` block in the global rule and all prompts.

## Execution choice

Plan complete and saved to `docs/superpowers/plans/2026-06-09-agent-code-indexing-plan.md`. Two execution options:

1. Subagent-Driven (recommended): dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution: execute tasks in-session with checkpoints using executing-plans.

Which approach?


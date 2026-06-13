# User and Agent Manuals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create two comprehensive manuals: one for human operators using Plastic Engineering Data Hub, and one for AI/automation agents maintaining, validating, and extending it.

**Architecture:** Keep the manuals as Markdown under `docs/` so they are versioned with the product and available offline. The human manual explains app behavior, user workflows, and support procedures without requiring code knowledge. The agent manual explains repo structure, safety rules, environment handling, verification, and handoff standards for future agentic workers.

**Tech Stack:** Markdown documentation, Docker Compose runbooks, Django REST backend, React/Vite frontend, PostgreSQL, Redis/Celery, Meilisearch, Caddy.

---

## File Structure

- Create: `docs/manual/user-manual.md`
  - Responsibility: End-user and administrator operating guide for the browser app.
  - Audience: Engineers, quality reviewers, project managers, operations/admin users, and client-side superusers.
- Create: `docs/manual/agent-manual.md`
  - Responsibility: Agent/operator guide for maintaining and validating the product without leaking secrets or breaking release data.
  - Audience: Codex agents, automation agents, and technical maintainers.
- Modify: `README.md`
  - Responsibility: Link the two manuals from the project entrypoint.
- Create: `docs/superpowers/plans/2026-06-13-user-and-agent-manuals-plan.md`
  - Responsibility: Saved plan for this documentation implementation.

## Manual Requirements

- Human manual must include prerequisites, installation, local startup, production deployment, first-run setup, updates, backup/restore, and deployment troubleshooting.
- Agent manual must include an operator-grade deployment runbook, environment validation, secret handling, service startup, migration, release seeding, smoke checks, rollback, and handoff expectations.
- Human manual must cover login, navigation, home, records, projects, documents, search, dashboards, tasks, audit, admin, imports, common workflows, roles, and troubleshooting.
- Agent manual must cover repository map, environment and secrets, verification discipline, data readiness, browser QA checklist, coding/documentation workflow, and handoff standards.
- Both manuals must avoid production secrets.
- Both manuals must use concrete commands and paths where relevant.
- README must make both manuals discoverable.

---

### Task 1: Save the Plan

**Files:**
- Create: `docs/superpowers/plans/2026-06-13-user-and-agent-manuals-plan.md`

- [ ] **Step 1: Create the plan file**

Write this file with the exact scope, file structure, task list, and manual requirements shown here.

- [ ] **Step 2: Confirm no placeholders are present**

Scan the plan content before saving. The words `TBD`, `TODO`, `fill in later`, and `placeholder section` must not appear.

Expected: The plan is immediately executable by another engineer or agent.

---

### Task 2: Write the Human User Manual

**Files:**
- Create: `docs/manual/user-manual.md`

- [ ] **Step 1: Create the manual skeleton**

Use these top-level sections:

```markdown
# Plastic Engineering Data Hub User Manual

## 1. What This System Is For
## 2. Access, Login, And Roles
## 3. Navigation Map
## 4. Home And Operational Overview
## 5. Records
## 6. Projects
## 7. Documents
## 8. Search
## 9. Dashboards
## 10. Task Inbox And Workflows
## 11. Audit
## 12. Admin
## 13. Import Wizard
## 14. Common End-To-End Workflows
## 15. Troubleshooting
## 16. Glossary
```

- [ ] **Step 2: Fill every section with concrete product behavior**

Include explicit examples for:

```text
status="archived"
type="project"
type="document"
type="raw_material" status="released"
```

- [ ] **Step 3: Add operator cautions**

State that user passwords, production secrets, and client-specific credentials belong in `.env` or the identity provider, not in tracked docs.

Expected: A new user can operate the app and a superuser can administer it without reading source code.

---

### Task 3: Write the Agent Manual

**Files:**
- Create: `docs/manual/agent-manual.md`

- [ ] **Step 1: Create the manual skeleton**

Use these top-level sections:

```markdown
# Plastic Engineering Data Hub Agent Manual

## 1. Operating Standard
## 2. Product And Architecture Summary
## 3. Repository Map
## 4. Environment And Secrets
## 5. Local Startup And Service Commands
## 6. Data Readiness And Release Dataset
## 7. Search And Navigation Contract
## 8. Browser QA Contract
## 9. Verification Matrix
## 10. Change Workflow For Agents
## 11. Documentation Workflow
## 12. Safety Rules
## 13. Handoff Template
## 14. Known Client-Critical Behaviors
```

- [ ] **Step 2: Fill every section with actionable instructions**

Include exact commands:

```sh
docker compose -f compose.yaml -f compose.dev.yaml ps
docker compose -f compose.yaml -f compose.dev.yaml exec backend python manage.py check
docker compose -f compose.yaml -f compose.dev.yaml exec backend python scripts/client_readiness_smoke.py
cd frontend && node node_modules/typescript/bin/tsc -b && node node_modules/vite/bin/vite.js build
```

- [ ] **Step 3: Add secret handling and handoff standards**

State that `.env` must not be committed and that `example.env` and `.env.example` contain only safe example values.

Expected: A future agent can safely continue product work, verify it, and hand it off without regressing user-facing behavior or leaking secrets.

---

### Task 4: Link Manuals From README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a documentation section after Quickstart or before Verification**

Add this text:

```markdown
## Manuals

- [Human User Manual](docs/manual/user-manual.md): Browser workflows for operators, engineers, quality reviewers, project owners, and administrators.
- [Agent Manual](docs/manual/agent-manual.md): Maintenance, verification, environment, and handoff rules for AI agents and technical maintainers.
```

- [ ] **Step 2: Keep release and operations links intact**

Do not remove existing links to `docs/release-checklist.md`, `docs/admin-guide.md`, or `docs/operations-guide.md`.

Expected: A reader landing on README can find the two manuals immediately.

---

## Self-Review

Spec coverage:
- Two manuals are planned and implemented as separate files.
- Installation, prerequisites, startup, deployment, update, backup, restore, and troubleshooting coverage is included.
- Human manual covers every major app area requested by the client-facing workflow.
- Agent manual covers environment, secrets, verification, browser QA, and handoff.
- README discoverability is included.

Placeholder scan:
- No task depends on unspecified future content.
- No production secrets are introduced.

Execution path:
- This documentation-only request is implemented in the current workspace after the user explicitly requested plan plus implementation.
- No runtime code, database migrations, or deployment settings are changed.


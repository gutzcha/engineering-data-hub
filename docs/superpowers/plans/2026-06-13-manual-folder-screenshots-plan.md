# Manual Folder And Screenshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the manuals into a dedicated documentation folder and add actual screenshots from the running Plastic Engineering Data Hub app.

**Architecture:** Create `docs/manual/` as the canonical manual package, with Markdown manuals at the folder root and PNG screenshots under `docs/manual/assets/screenshots/`. Keep README links updated so humans and agents enter the manual package from the repository root. Embed screenshots in the human manual near the app areas they illustrate.

**Tech Stack:** Markdown documentation, in-app browser screenshots, Docker-hosted local app at `http://127.0.0.1:5173/`, PNG assets committed with docs.

---

## File Structure

- Create: `docs/manual/README.md`
  - Responsibility: Manual package landing page with links to both manuals and screenshots.
- Move: `docs/user-manual.md` to `docs/manual/user-manual.md`
  - Responsibility: Human user manual with embedded screenshots.
- Move: `docs/agent-manual.md` to `docs/manual/agent-manual.md`
  - Responsibility: Agent and technical operator manual.
- Create: `docs/manual/assets/screenshots/*.png`
  - Responsibility: Actual screenshots captured from the running app.
- Modify: `README.md`
  - Responsibility: Link to the new manual folder paths.
- Modify: `docs/superpowers/plans/2026-06-13-user-and-agent-manuals-plan.md`
  - Responsibility: Point future readers to the manual folder.

## Screenshot Set

Capture these app pages from the running local instance:

- `01-home-operational-overview.png` from `/`
- `02-records-list.png` from `/records`
- `03-projects.png` from `/projects`
- `04-documents.png` from `/documents`
- `05-search.png` from `/search`
- `06-dashboards.png` from `/dashboards`
- `07-tasks.png` from `/tasks`
- `08-admin.png` from `/admin`
- `09-audit.png` from `/audit`
- `10-import-wizard.png` from `/imports`

If the browser session is already authenticated, use it. If it is not authenticated, sign in through the local app using the configured local credentials already present in the environment and do not write the password into any tracked file.

---

### Task 1: Save The Plan

**Files:**
- Create: `docs/superpowers/plans/2026-06-13-manual-folder-screenshots-plan.md`

- [ ] **Step 1: Create the plan file**

Create this file with the folder structure, screenshot set, and execution tasks shown here.

- [ ] **Step 2: Confirm scope**

Expected: The plan changes documentation only and does not modify runtime code, database schema, or deployment configuration.

---

### Task 2: Capture Screenshots

**Files:**
- Create: `docs/manual/assets/screenshots/01-home-operational-overview.png`
- Create: `docs/manual/assets/screenshots/02-records-list.png`
- Create: `docs/manual/assets/screenshots/03-projects.png`
- Create: `docs/manual/assets/screenshots/04-documents.png`
- Create: `docs/manual/assets/screenshots/05-search.png`
- Create: `docs/manual/assets/screenshots/06-dashboards.png`
- Create: `docs/manual/assets/screenshots/07-tasks.png`
- Create: `docs/manual/assets/screenshots/08-admin.png`
- Create: `docs/manual/assets/screenshots/09-audit.png`
- Create: `docs/manual/assets/screenshots/10-import-wizard.png`

- [ ] **Step 1: Create screenshot folder**

Run:

```powershell
New-Item -ItemType Directory -Force docs\manual\assets\screenshots
```

- [ ] **Step 2: Capture each route through the in-app browser**

Use the in-app browser screenshot API after navigation and page load.

Expected: Each PNG is an actual screenshot from `http://127.0.0.1:5173/`, not a mockup.

---

### Task 3: Move Manuals Into Manual Folder

**Files:**
- Move: `docs/user-manual.md` to `docs/manual/user-manual.md`
- Move: `docs/agent-manual.md` to `docs/manual/agent-manual.md`

- [ ] **Step 1: Move the files**

Run:

```powershell
Move-Item docs\user-manual.md docs\manual\user-manual.md
Move-Item docs\agent-manual.md docs\manual\agent-manual.md
```

- [ ] **Step 2: Keep filenames stable inside the folder**

Expected: Human manual is `docs/manual/user-manual.md`; agent manual is `docs/manual/agent-manual.md`.

---

### Task 4: Embed Screenshots In Human Manual

**Files:**
- Modify: `docs/manual/user-manual.md`

- [ ] **Step 1: Add screenshot references**

Embed images after the sections they illustrate using relative paths like:

```markdown
![Home operational overview](assets/screenshots/01-home-operational-overview.png)
```

- [ ] **Step 2: Keep text concise**

Expected: Screenshots support the manual without replacing written instructions.

---

### Task 5: Create Manual Folder Landing Page And Update Links

**Files:**
- Create: `docs/manual/README.md`
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-06-13-user-and-agent-manuals-plan.md`

- [ ] **Step 1: Add manual package landing page**

Create a README with links to the human manual, agent manual, and screenshot folder.

- [ ] **Step 2: Update root README**

Change manual links from `docs/user-manual.md` and `docs/agent-manual.md` to `docs/manual/user-manual.md` and `docs/manual/agent-manual.md`.

- [ ] **Step 3: Update prior plan references**

Point future readers to `docs/manual/`.

Expected: No root README link points to the old manual paths.

---

## Self-Review

Spec coverage:
- Dedicated manual folder is planned.
- Actual app screenshots are planned.
- Human and agent manuals remain separate.
- README discoverability remains intact.

Placeholder scan:
- No screenshots are described as future work.
- No production secrets are written into the plan.

Execution path:
- Use the in-app browser to capture screenshots from the running local app.
- Keep all changes documentation-only.

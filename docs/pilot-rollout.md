# Pilot Rollout

This plan introduces the Plastic Engineering Data Hub to a controlled pilot group before wider rollout.

## Goals

The pilot should prove that the starter configuration supports daily engineering work, traceability, document control, and reporting without forcing a large customization project first.

Primary outcomes:

1. Users can create and find product, raw-material, product-spec, supplier, customer, and project records.
2. Engineering release, product spec release, raw material approval, and project gate review workflows are understandable.
3. Managed folders and document attachments support controlled work.
4. Dashboards expose document gaps, workload, and missing data.
5. Admins can publish safe configuration changes and restore from backup if needed.

## Stakeholders

| Stakeholder | Responsibilities |
| --- | --- |
| Executive sponsor | Confirms pilot scope, timeline, success criteria, and go/no-go decision. |
| Engineering lead | Owns product, spec, project, and test-method usage. |
| Quality lead | Owns document control, release review, audit evidence, and validation checklist. |
| Supplier quality or purchasing lead | Owns supplier and raw-material onboarding. |
| System admin | Owns users, roles, configuration drafts, backups, and restore drills. |
| Pilot users | Run real scenarios, report friction, and validate training material. |
| IT support | Owns infrastructure, VPN or internal access, certificates, and monitoring. |

## Phased Rollout

### Phase 0: Preparation

Duration: 1 to 2 weeks.

Tasks:

1. Install the application in a pilot environment.
2. Publish the starter configuration.
3. Configure roles, groups, and object permissions.
4. Confirm backups and complete one restore drill.
5. Pick pilot records: 5 to 10 products, 10 to 20 raw materials, active suppliers, and 2 to 3 active projects.
6. Define document type names for TDS, SDS, compliance, specification, drawing, and work instruction files.

Exit criteria:

1. Pilot users can sign in.
2. Admins can create a draft, validate it, and publish it.
3. Backup and restore evidence is recorded.

### Phase 1: Seed And Validate Data

Duration: 1 week.

Tasks:

1. Clean source spreadsheets and map columns to starter field keys.
2. Import suppliers first.
3. Import raw materials and link them to suppliers.
4. Import products, specs, and projects.
5. Attach or migrate representative documents.
6. Create traceability relationships for selected products, materials, specs, suppliers, customers, and projects.

Exit criteria:

1. Sample records have correct titles, codes, statuses, and required fields.
2. Record references resolve to the intended records.
3. Dashboards show expected counts and known missing documents.
4. Audit history shows import and edit activity.

### Phase 2: Workflow Pilot

Duration: 2 weeks.

Tasks:

1. Run one product through Engineering Record Release.
2. Run one product spec through Product Spec Release.
3. Run one raw material through Raw Material Approval.
4. Run one active project through Project Gate Review.
5. Review task inbox behavior, bottleneck reporting, and audit history.

Exit criteria:

1. Each starter workflow is completed at least once.
2. Reviewers understand required fields, documents, and signoff points.
3. Any workflow wording or permission gaps are documented.

### Phase 3: Pilot Review

Duration: 1 week.

Tasks:

1. Review success metrics.
2. Triage issues into must-fix, later improvement, and training categories.
3. Publish any low-risk configuration refinements.
4. Decide whether to expand, repeat the pilot, or pause.

Exit criteria:

1. Sponsor approves a rollout decision.
2. Open risks have owners and dates.
3. Cutover or rollback plan is current.

## Migration And Import Approach

Use a staged migration instead of one large spreadsheet.

Recommended order:

1. Suppliers.
2. Raw materials.
3. Customers.
4. Products.
5. Product specs.
6. Projects.
7. Documents and relationships.

Mapping rules:

1. Preserve legacy identifiers in a field or notes column when they differ from generated record codes.
2. Normalize supplier and customer names before import.
3. Convert dates to ISO format.
4. Keep controlled files in the document system and link them to records.
5. Import a small sample first and reconcile every field before bulk import.

## Validation Checklist

Before pilot users begin:

1. Active configuration is the intended version.
2. Object fields match the pilot data map.
3. Roles and permissions match the access matrix.
4. At least one user from each pilot role can sign in.
5. Managed folder generation works for product and raw material records.
6. Documents can be uploaded, attached, viewed, and audited.
7. Dashboards load for pilot users with expected permission filtering.
8. Import templates match current field keys.
9. Backups run successfully and restore has been tested.
10. Audit logs are visible to authorized admins.

After each workflow test:

1. Required fields and documents are enforced by process.
2. Tasks have the correct owner or role.
3. Workflow state changes are recorded.
4. Released or approved records are easy to find.
5. Dashboards reflect the new workload or document status.

## Training

Run short role-based sessions:

| Audience | Training focus |
| --- | --- |
| All pilot users | Navigation, search, record detail pages, saved views, dashboards. |
| Engineers | Product, spec, project, relationships, folders, workflow actions. |
| Quality reviewers | Document health, release evidence, audit review, required documents. |
| Supplier quality or purchasing | Supplier records, raw material approvals, compliance documents. |
| Admins | Configuration drafts, validation, publishing, permissions, imports, backups. |

Provide a quick reference with field definitions, document type names, workflow states, and support contacts.

## Success Metrics

Track these measures during the pilot:

1. At least 90 percent of selected pilot records migrated without manual correction after sample validation.
2. All four starter workflows completed at least once.
3. Pilot users can find a target product or material in under two minutes.
4. Required document gaps are visible on the Document Health or Missing Data dashboards.
5. No unresolved high-severity permission or data-loss issues.
6. Admins complete one configuration draft validation and one manual backup.
7. Pilot user satisfaction is positive enough to expand, with specific improvement requests captured.

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Source data is inconsistent | Clean and sample-import data before bulk migration. |
| Users bypass document control | Train document attachment workflow and review dashboard gaps weekly. |
| Permissions are too broad | Start with least privilege and review access requests twice weekly. |
| Workflow labels do not match local language | Adjust labels in a draft while keeping keys stable. |
| Reports expose incomplete data | Mark pilot dashboards as operational indicators, not compliance evidence, until validation completes. |
| Cutover blocks daily work | Keep legacy spreadsheets read-only but available during the rollback window. |

## Cutover

Use cutover only after the sponsor approves the pilot review.

Cutover steps:

1. Announce the cutover window and support channel.
2. Run a manual backup and record the backup id.
3. Freeze legacy edits or mark the legacy source read-only.
4. Import final delta records and documents.
5. Validate dashboards, workflow tasks, and sample searches.
6. Confirm support coverage for the first business day after cutover.

## Rollback

Rollback should be rare but explicit.

Rollback triggers:

1. Data migration creates widespread incorrect records.
2. Critical users cannot access required records.
3. Workflow or document control blocks urgent release work.
4. Infrastructure instability prevents normal use.

Rollback steps:

1. Stop new edits in the hub.
2. Capture audit logs and issue notes.
3. Restore the last known good backup if data must be reverted.
4. Reopen the legacy process for active work.
5. Fix root causes in a non-production environment.
6. Repeat validation before resuming rollout.

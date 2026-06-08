# Admin Guide

This guide covers the starter Plastic Engineering Data Hub configuration and the routine administration tasks needed to keep it controlled.

## Starter Configuration

The default starter configuration is stored in `backend/apps/config_registry/fixtures/plastic_engineering_v1.json`. When no configuration has been published, creating a configuration draft starts from this fixture.

The starter object model includes:

| Object type | Starter fields |
| --- | --- |
| Product | commercial_name, internal_grade, resin_family, application, color, regulatory_notes, status_notes |
| Raw Material | supplier_material_code, material_family, supplier, melt_flow_index, density, color, technical_data_sheet, compliance_documents |
| Product Spec | spec_number, product, revision, effective_date, controlled_document, release_notes |
| Supplier | supplier_name, supplier_code, contact_email, approved_status |
| Customer | customer_name, customer_code, market_segment |
| Project | project_name, project_type, target_launch_date, project_owner, linked_product |
| Test Method | method_name, method_number, controlled_document, method_scope |
| Document | document_title, document_type, revision, effective_date, controlled_file |

The starter relationship types preserve traceability between products, materials, specs, suppliers, customers, projects, and documents.

## Workflows

The starter workflows are:

| Workflow | Purpose |
| --- | --- |
| Engineering Record Release | Releases product, document, and test-method records through engineering and quality review. |
| Product Spec Release | Controls spec number, product link, revision, controlled document, approval, and effective date. |
| Raw Material Approval | Reviews supplier, compliance documents, technical data, and material approval status. |
| Project Gate Review | Moves projects from idea through scoping, development, launch review, and closeout. |

Treat workflow keys as stable identifiers. You can rename labels for local wording, but changing keys can break saved references and reports.

Publishing configuration bootstraps these starter definitions into the runtime workflow tables. Runtime rows created from configuration are marked as config-managed and are updated by later publishes; manually created runtime workflows with conflicting keys are left untouched.

## Folder Templates

The starter managed-folder templates are:

| Template | Pattern | Typical contents |
| --- | --- | --- |
| product_standard | `Products/{code}_{title}` | Specifications, drawings, materials, testing, project files, working files. |
| raw_material_standard | `Raw_Materials/{code}_{title}` | Supplier documents, technical data, compliance, working files. |
| project_standard | `Projects/{code}_{title}` | Charter, gate reviews, trials, customer inputs, working files. |
| supplier_standard | `Suppliers/{code}_{title}` | Qualification, compliance, correspondence, working files. |

Keep folder patterns deterministic and based on stable record values such as code and title. Avoid including dates or status values that may change after folder creation.

Managed folder generation supports the product, raw material, project, and supplier starter templates at runtime.

## Dashboards

The starter dashboard definitions are published into global runtime dashboards for operational reporting:

| Dashboard | Main widgets |
| --- | --- |
| Engineering Overview | Count by status, count by object type, recent changes. |
| Document Health | Missing required documents, document record status. |
| Project Workload | Overdue project tasks, workflow bottlenecks, project status. |
| Missing Data | Product records missing status notes and raw materials missing required documents. |

Dashboard widgets use the reports widget vocabulary: `count_by_status`, `count_by_object_type`, `overdue_project_tasks`, `missing_required_documents`, `recent_changes`, and `workflow_bottlenecks`.

Runtime dashboards created from configuration are marked as config-managed and are updated by later publishes. User-owned dashboards and unmanaged global dashboards are not overwritten.

## Roles And Permissions

Create role groups around actual job duties, then grant object permissions to those groups.

Recommended starting roles:

| Role | Typical access |
| --- | --- |
| System Admin | Configuration, users, backups, audit access, and emergency support. |
| Engineering Admin | Admin access to products, specs, projects, test methods, and workflows. |
| Quality Reviewer | Review and release access for specs, documents, raw materials, and audit evidence. |
| Purchasing Or Supplier Quality | Supplier and raw-material view/edit access. |
| Read Only Viewer | View released records and dashboards for selected object types. |

Use the least-permission role that supports the job. For pilot users, start narrow and expand only after a review of failed access attempts and support requests.

## Import And Export

Use imports for controlled migration from spreadsheets or legacy systems.

Before import:

1. Publish the configuration version that contains the target object types and fields.
2. Normalize source column names to the starter field keys.
3. Decide how record codes will be generated or mapped.
4. Split reference data into separate imports: suppliers first, raw materials second, products and specs after that.
5. Run a small sample import and validate records before importing the full set.

For export, prefer saved views or reports that include stable identifiers such as record id, object type, code, title, status, and updated timestamp.

## Documents

Attach controlled documents to records instead of embedding file paths in notes. Use document types consistently, especially for TDS, SDS, compliance, specification, drawing, and work instruction documents.

Document health dashboards depend on consistent document type naming. If you rename document types, update dashboard requirements at the same time.

## Audits

Audit history is the source of truth for configuration publishing, record changes, workflow transitions, document actions, and backup operations. Admins should review audit events after configuration changes and before pilot cutover.

Recommended checks:

1. Confirm who published the active configuration and when.
2. Review failed validation or publish attempts.
3. Spot-check record creation and import events after migration.
4. Confirm workflow transitions record the actor and state change.

## Backups

Backups are covered operationally in `docs/operations-guide.md`. Admins should verify that scheduled backups are running and that restore drills have been completed before production cutover.

Minimum backup practices:

1. Keep nightly backups enabled.
2. Run a manual backup before configuration publish, bulk import, or application update.
3. Record the backup id in the change ticket.
4. Test restore on a non-production environment before relying on a backup plan.

## Customizing Configuration Safely

Use this process for configuration changes:

1. Create a draft from the current published configuration.
2. Make one logical change at a time.
3. Keep keys lowercase snake_case and stable after publish.
4. Use only supported field types: text, long_text, number, date, boolean, choice, multi_choice, record_ref, file_ref, url, user_ref.
5. Validate the draft.
6. Export or screenshot the validation result for the change record.
7. Run a manual backup.
8. Publish during an agreed change window.
9. Test record creation, folders, workflows, dashboards, and imports that depend on the changed fields.

Configuration editing is role-gated. Users in the Configuration Admin role can create, edit, validate, and publish normal non-destructive configuration drafts. Destructive schema changes require System Admin approval and an explicit publish confirmation.

The system treats these as destructive schema changes:

1. Removing an object type.
2. Removing a field, such as `material_family`.
3. Changing a field type.
4. Adding or enabling a required field.
5. Enabling uniqueness on a field.
6. Removing a choice or multi-choice option.
7. Changing a record reference target.

Avoid deleting fields during a pilot unless the data was never used. Prefer deprecating a field in the label or notes, then remove it after exports and reports have been updated. Removing a field from configuration does not erase historical record JSON; it hides the field from normal forms until an explicit data cleanup or migration is run.

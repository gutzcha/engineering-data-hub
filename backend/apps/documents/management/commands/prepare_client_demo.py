from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.config_registry.models import ConfigurationDraft, ConfigurationVersion, FieldDefinition
from apps.documents.management.commands.seed_demo_documents import (
    GENERATED_DOCUMENTS,
    SOURCE_DOCUMENTS,
    generated_docx,
    note_document_link,
)
from apps.documents.models import Document, DocumentRevision
from apps.documents.views import _create_or_replace_revision, _document_snapshot
from apps.folders.models import FolderChangeEvent, ManagedFolder
from apps.imports.models import ImportAuditEvent, ImportJob
from apps.projects.models import Project, ProjectBoardColumn, ProjectMilestone, ProjectTask
from apps.records.models import Record
from apps.search.tasks import rebuild_all_indexes
from apps.workflows.models import WorkflowDefinition, WorkflowInstance, WorkflowTask


RELEASE_ADMIN_PASSWORD_ENV = "RELEASE_ADMIN_PASSWORD"
QA_USER_PREFIXES = ("qa_", "e2e", "codex", "demo_")
QA_USERNAMES = {
    "client_admin",
    "client_readiness_seed",
    "codex-e2e",
    "demo_engineer",
    "demo_viewer",
    "e2e_auto",
    "qa_browser_smoke",
    "qa_config_admin",
    "qa_engineer",
    "qa_readonly",
    "qa_system_admin",
}
NOISE_PATTERNS = (
    "qa-",
    "qa_",
    "qa ",
    " qa",
    "qa client",
    "qa-client",
    "client_demo",
    "client-demo",
    "client-readiness",
    "demo",
    "probe",
    "debug",
    "operator-search",
    "pw-rm-",
    "pw traceable",
)


@dataclass(frozen=True)
class MaterialProfile:
    code: str
    title: str
    family: str
    resin: str
    supplier: str
    grade: str
    application: str
    color: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ProjectProfile:
    code: str
    name: str
    status: str
    project_type: str
    description: str
    material_codes: tuple[str, ...]


MATERIALS = {
    "pp": MaterialProfile(
        "MAT-PP-001",
        "Polypropylene High Flow Resin",
        "Polyolefin",
        "PP",
        "Northstar Polymer Supply",
        "PP-HF-1200",
        "Thin-wall injection molding housings",
        "Natural",
        ("polypropylene", "pp", "injection-molding", "thin-wall"),
    ),
    "rhdpe": MaterialProfile(
        "MAT-RHDPE-001",
        "Recycled HDPE Food Contact Resin",
        "Polyolefin",
        "HDPE",
        "Circular Resin Partners",
        "R-HDPE-FC-70",
        "Sustainable packaging qualification",
        "Natural",
        ("recycled", "hdpe", "food-contact", "supplier-approval"),
    ),
    "pc": MaterialProfile(
        "MAT-PC-001",
        "Optical Polycarbonate Resin",
        "Engineering Thermoplastic",
        "PC",
        "ClearView Polymers",
        "PC-OPT-940",
        "Transparent impact-resistant covers",
        "Clear",
        ("polycarbonate", "pc", "optical", "impact"),
    ),
    "pcabs": MaterialProfile(
        "MAT-PCABS-FR-001",
        "Flame-Retardant PC/ABS Blend",
        "Engineering Blend",
        "PC/ABS",
        "Alloy Materials Group",
        "PCABS-FR-22",
        "Electronics enclosures",
        "Black",
        ("pcabs", "pc/abs", "abs", "flame-retardant"),
    ),
    "nylon": MaterialProfile(
        "MAT-PA66-GF30-001",
        "Nylon PA66 GF30 Resin",
        "Engineering Thermoplastic",
        "PA66",
        "FiberForm Compounds",
        "PA66-GF30",
        "Glass-filled structural brackets",
        "Black",
        ("nylon", "polyamide", "pa66", "glass-filled"),
    ),
    "pom": MaterialProfile(
        "MAT-POM-001",
        "Acetal POM Natural Resin",
        "Engineering Thermoplastic",
        "POM",
        "Precision Resin Co.",
        "POM-NAT-500",
        "Low-friction precision gears",
        "Natural",
        ("acetal", "pom", "delrin", "low-friction"),
    ),
    "petg": MaterialProfile(
        "MAT-PETG-001",
        "Clear PETG Sheet Resin",
        "Copolyester",
        "PETG",
        "SheetGrade Plastics",
        "PETG-CLR-810",
        "Clear thermoformed display panels",
        "Clear",
        ("petg", "thermoforming", "clear", "sheet"),
    ),
    "tpu": MaterialProfile(
        "MAT-TPU-85A-001",
        "TPU 85A Elastomer Resin",
        "Elastomer",
        "TPU",
        "FlexTech Elastomers",
        "TPU-85A-EX",
        "Flexible extrusion profiles",
        "Natural",
        ("tpu", "extrusion", "flexible", "elastomer"),
    ),
    "pvc": MaterialProfile(
        "MAT-PVC-001",
        "Rigid PVC Compound",
        "Vinyl",
        "PVC",
        "VinylWorks Materials",
        "PVC-RG-300",
        "Chemical-resistant fittings",
        "White",
        ("pvc", "vinyl", "chemical-resistant", "compound"),
    ),
    "pmma": MaterialProfile(
        "MAT-PMMA-001",
        "Optical PMMA Acrylic Resin",
        "Acrylic",
        "PMMA",
        "Acrylux Supply",
        "PMMA-OPT-200",
        "Transparent lenses and light pipes",
        "Clear",
        ("pmma", "acrylic", "optical", "transparent"),
    ),
    "pla": MaterialProfile(
        "MAT-PLA-001",
        "PLA Filament Resin",
        "Biopolymer",
        "PLA",
        "Additive Materials Lab",
        "PLA-PRINT-01",
        "Additive manufacturing prototypes",
        "Natural",
        ("pla", "additive-manufacturing", "biopolymer", "filament"),
    ),
    "hips": MaterialProfile(
        "MAT-HIPS-001",
        "HIPS White Polystyrene Resin",
        "Styrenic",
        "HIPS",
        "Styrene Solutions",
        "HIPS-WHT-410",
        "Impact-modified appliance panels",
        "White",
        ("hips", "polystyrene", "impact", "appliance"),
    ),
}

PROJECTS = (
    ProjectProfile(
        "PRJ-QUAL-001",
        "Lightweight Housing Material Qualification",
        Project.Status.ACTIVE,
        "Material Change",
        "Qualify PP and PC/ABS options for a lighter molded electronics housing while preserving weld-line strength and flame-rating requirements.",
        ("MAT-PP-001", "MAT-PCABS-FR-001"),
    ),
    ProjectProfile(
        "PRJ-QUAL-002",
        "Recycled HDPE Supplier Approval",
        Project.Status.PLANNING,
        "Regulatory",
        "Approve recycled HDPE as a food-contact packaging resin by linking SDS, supplier CAPA, and incoming-lot inspection criteria.",
        ("MAT-RHDPE-001",),
    ),
    ProjectProfile(
        "PRJ-QUAL-003",
        "Transparent PETG Processing Window",
        Project.Status.COMPLETE,
        "New Product",
        "Document the PETG sheet processing window and release guidance for clear thermoformed display panels.",
        ("MAT-PETG-001",),
    ),
)


class Command(BaseCommand):
    help = "Prepare a clean client release dataset and remove QA/probe artifacts from a non-production workspace."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-document-seed",
            action="store_true",
            help="Do not backfill missing curated documents before cleanup.",
        )
        parser.add_argument(
            "--confirm-destructive-reset",
            action="store_true",
            help="Required. Confirms this non-production database may be reset for client release readiness.",
        )
        parser.add_argument(
            "--admin-password",
            default=os.environ.get(RELEASE_ADMIN_PASSWORD_ENV),
            help=(
                "Password for the release administrator. Prefer RELEASE_ADMIN_PASSWORD from a local .env file "
                "or secret manager."
            ),
        )

    def handle(self, *args, **options):
        self._validate_reset_allowed(options)
        if not options["admin_password"]:
            raise CommandError(
                f"Set {RELEASE_ADMIN_PASSWORD_ENV} in the local .env file or pass --admin-password explicitly."
            )
        if not options["skip_document_seed"]:
            call_command("seed_demo_documents", limit=len(SOURCE_DOCUMENTS), offline=True)

        with transaction.atomic():
            actor = self._prepare_users(options["admin_password"])
            supplier_records = self._prepare_suppliers(actor)
            material_records = self._prepare_materials(actor, supplier_records)
            self._dedupe_and_attach_documents(material_records)
            self._sanitize_configuration()
            self._remove_noisy_operational_data({**supplier_records, **material_records})
            project_records = self._prepare_projects(actor)
            self._attach_project_documents(project_records, actor)
            workflow_tasks = self._prepare_workflow_tasks(actor, material_records)
            self._reset_audit_log()
            self._write_client_audit(actor, material_records, project_records)

        index_counts = rebuild_all_indexes()
        summary = self._summary(index_counts, workflow_tasks)
        self.stdout.write(self.style.SUCCESS(summary))

    def _validate_reset_allowed(self, options):
        if not options["confirm_destructive_reset"]:
            raise CommandError("Refusing to reset data without --confirm-destructive-reset.")
        if os.environ.get("APP_ENV", "dev").lower() == "prod":
            raise CommandError("Refusing to run destructive release preparation when APP_ENV=prod.")

    def _prepare_users(self, admin_password):
        User = get_user_model()
        release_admin = self._upsert_user(
            "operations_admin",
            admin_password,
            first_name="Operations",
            last_name="Admin",
            email="operations.admin@plastic-engineering.local",
            is_staff=True,
            is_superuser=True,
        )
        self._upsert_user(
            "process_engineer",
            None,
            first_name="Process",
            last_name="Engineer",
            email="process.engineer@plastic-engineering.local",
            is_staff=True,
            is_superuser=False,
        )
        self._upsert_user(
            "quality_manager",
            None,
            first_name="Quality",
            last_name="Manager",
            email="quality.manager@plastic-engineering.local",
            is_staff=True,
            is_superuser=False,
        )
        self._upsert_user(
            "read_only_auditor",
            None,
            first_name="Read Only",
            last_name="Auditor",
            email="auditor@plastic-engineering.local",
            is_staff=False,
            is_superuser=False,
        )
        noisy_users = User.objects.filter(username__in=QA_USERNAMES)
        for prefix in QA_USER_PREFIXES:
            noisy_users = noisy_users | User.objects.filter(username__startswith=prefix)
        release_usernames = {"operations_admin", "process_engineer", "quality_manager", "read_only_auditor"}
        for user in noisy_users.exclude(username__in=release_usernames):
            user.username = f"archived-user-{user.pk}"
            user.first_name = "Archived"
            user.last_name = "User"
            user.email = f"archived-user-{user.pk}@example.invalid"
            user.is_active = False
            user.is_staff = False
            user.is_superuser = False
            user.save(update_fields=["username", "first_name", "last_name", "email", "is_active", "is_staff", "is_superuser"])
        return release_admin

    def _upsert_user(self, username, password, **defaults):
        User = get_user_model()
        user, _ = User.objects.update_or_create(
            username=username,
            defaults={
                **defaults,
                "is_active": True,
            },
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(update_fields=["password", "first_name", "last_name", "email", "is_staff", "is_superuser", "is_active"])
        return user

    def _prepare_suppliers(self, actor):
        supplier_records = {}
        for index, supplier_name in enumerate(sorted({profile.supplier for profile in MATERIALS.values()}), start=1):
            code = f"SUP-{index:03d}"
            supplier, _ = Record.objects.update_or_create(
                code=code,
                defaults={
                    "object_type_key": "supplier",
                    "title": supplier_name,
                    "status": Record.Status.RELEASED,
                    "schema_version": 1,
                    "created_by": actor,
                    "updated_by": actor,
                    "data": {
                        "supplier_name": supplier_name,
                        "supplier_code": code,
                        "contact_email": "",
                        "approved_status": "Approved",
                        "release_ready": True,
                    },
                },
            )
            supplier_records[supplier_name] = supplier
        return supplier_records

    def _prepare_materials(self, actor, supplier_records):
        material_records = {}
        for key, profile in MATERIALS.items():
            supplier_record = supplier_records[profile.supplier]
            record, _ = Record.objects.update_or_create(
                code=profile.code,
                defaults={
                    "object_type_key": "raw_material",
                    "title": profile.title,
                    "status": Record.Status.RELEASED,
                    "schema_version": 1,
                    "created_by": actor,
                    "updated_by": actor,
                    "data": {
                        "commercial_name": profile.title,
                        "material_family": material_family_choice(profile),
                        "material_family_label": profile.family,
                        "resin_family": profile.resin,
                        "supplier": str(supplier_record.pk),
                        "supplier_name": profile.supplier,
                        "supplier_material_code": profile.grade,
                        "application": profile.application,
                        "color": profile.color,
                        "melt_flow_index": reference_melt_flow_index(profile.resin),
                        "density": reference_density(profile.resin),
                        "tags": list(profile.tags),
                        "release_ready": True,
                        "linked_documents": [],
                    },
                },
            )
            material_records[key] = record
        return material_records

    def _dedupe_and_attach_documents(self, material_records):
        curated_titles = self._curated_titles()
        keep_document_ids = []

        for title in sorted(curated_titles):
            documents = list(Document.objects.filter(title=title).order_by("-updated_at", "-id"))
            if not documents:
                continue
            keep = documents[0]
            profile_key = self._profile_key_for_document(title)
            owner = material_records[profile_key]
            if keep.owner_record_id != owner.pk:
                keep.owner_record = owner
                keep.save(update_fields=["owner_record", "updated_at"])
            keep_document_ids.append(keep.pk)
            note_document_link(owner, title)

            duplicate_ids = [document.pk for document in documents[1:]]
            if duplicate_ids:
                Document.objects.filter(pk__in=duplicate_ids).delete()

        Document.objects.exclude(pk__in=keep_document_ids).delete()

    def _sanitize_configuration(self):
        for version in ConfigurationVersion.objects.all():
            clean_data, changed = sanitize_configuration_data(version.data)
            if changed:
                ConfigurationVersion.objects.filter(pk=version.pk).update(data=clean_data)

        for draft in ConfigurationDraft.objects.all():
            clean_data, changed = sanitize_configuration_data(draft.data)
            if changed:
                draft.data = clean_data
                draft.save(update_fields=["data", "updated_at"])

        FieldDefinition.objects.filter(
            Q(key__icontains="qa_operator")
            | Q(label__icontains="QA Operator")
            | Q(key__icontains="client_readiness")
            | Q(key__icontains="pw_rm")
        ).delete()

    def _remove_noisy_operational_data(self, material_records):
        keep_record_ids = {record.pk for record in material_records.values()}

        Project.objects.all().delete()
        WorkflowInstance.objects.all().delete()
        ImportAuditEvent.objects.all().delete()
        ImportJob.objects.all().delete()
        FolderChangeEvent.objects.all().delete()
        ManagedFolder.objects.all().delete()

        project_record_ids = list(Record.objects.filter(object_type_key="project").values_list("pk", flat=True))
        self._delete_record_versions(project_record_ids)
        Record.objects.filter(pk__in=project_record_ids).delete()

        legacy_ids = list(Record.objects.exclude(pk__in=keep_record_ids).values_list("pk", flat=True))
        if legacy_ids:
            self._delete_record_versions(legacy_ids)
            Record.objects.filter(pk__in=legacy_ids).delete()

    def _prepare_projects(self, actor):
        project_records = []
        today = timezone.localdate()
        for index, profile in enumerate(PROJECTS):
            related_materials = list(Record.objects.filter(code__in=profile.material_codes).order_by("code"))
            record, _ = Record.objects.update_or_create(
                code=profile.code,
                defaults={
                    "object_type_key": "project",
                    "title": profile.name,
                    "status": Record.Status.RELEASED,
                    "schema_version": 1,
                    "created_by": actor,
                    "updated_by": actor,
                    "data": {
                        "project_name": profile.name,
                        "project_type": profile.project_type,
                        "project_status": profile.status,
                        "target_launch_date": (today + timedelta(days=21 + index * 14)).isoformat(),
                        "project_owner": str(actor.pk),
                        "related_material_codes": list(profile.material_codes),
                        "tags": ["release", "project", "traceability"],
                        "application": "Engineering qualification",
                        "release_ready": True,
                    },
                },
            )
            project, _ = Project.objects.update_or_create(
                record=record,
                defaults={
                    "name": profile.name,
                    "description": profile.description,
                    "status": profile.status,
                    "start_date": today - timedelta(days=30 - index * 7),
                    "target_date": today + timedelta(days=21 + index * 14),
                    "owner": actor,
                    "created_by": actor,
                    "updated_by": actor,
                },
            )
            project_records.append(record)
            self._prepare_project_board(project, related_materials, actor)
        return project_records

    def _prepare_project_board(self, project, related_materials, actor):
        columns = {}
        for sort_order, (key, title) in enumerate((("todo", "To Do"), ("doing", "In Progress"), ("done", "Done"))):
            column, _ = ProjectBoardColumn.objects.update_or_create(
                project=project,
                key=key,
                defaults={"title": title, "sort_order": sort_order, "wip_limit": 4 if key == "doing" else None},
            )
            columns[key] = column

        milestone, _ = ProjectMilestone.objects.update_or_create(
            project=project,
            title="Qualification release decision",
            defaults={"target_date": timezone.localdate() + timedelta(days=21), "sort_order": 1},
        )

        task_specs = (
            ("Review linked material documents", ProjectTask.State.IN_PROGRESS, "doing"),
            ("Confirm record traceability links", ProjectTask.State.TODO, "todo"),
            ("Publish qualification summary", ProjectTask.State.DONE, "done"),
        )
        for sort_order, (title, state, column_key) in enumerate(task_specs):
            material_hint = ", ".join(record.code for record in related_materials) or project.record.code
            ProjectTask.objects.update_or_create(
                project=project,
                title=title,
                defaults={
                    "description": f"{title} for {material_hint}.",
                    "state": state,
                    "column": columns[column_key],
                    "milestone": milestone,
                    "assignee_user": actor,
                    "assignee_role": "Engineering",
                    "due_date": timezone.localdate() + timedelta(days=5 + sort_order * 4),
                    "estimated_hours": 2 + sort_order,
                    "sort_order": sort_order,
                    "created_by": actor,
                    "updated_by": actor,
                },
            )

    def _attach_project_documents(self, project_records, actor):
        for record in project_records:
            related_materials = ", ".join(record.data.get("related_material_codes", [])) or "linked materials"
            project_status = record.data.get("project_status", "active")
            document_specs = (
                (
                    f"{record.title} Qualification Summary",
                    "project_summary",
                    (
                        f"Project qualification summary for {record.title}.\n\n"
                        f"Related materials: {related_materials}.\n"
                        f"Current project status: {project_status}.\n"
                        "Scope: trace material documents, experiment summaries, supplier controls, "
                        "and release tasks to a single project decision package."
                    ),
                ),
                (
                    f"{record.title} Release Decision Record",
                    "release_decision",
                    (
                        f"Release decision record for {record.title}.\n\n"
                        f"Decision context: {record.data.get('project_type', 'qualification')}.\n"
                        f"Evidence package: {related_materials} plus controlled SDS, TDS, processing guide, "
                        "experiment summary, and open workflow task history.\n"
                        "Disposition: ready for stakeholder review with traceable source records."
                    ),
                ),
            )

            for title, document_type, body in document_specs:
                document, _ = Document.objects.get_or_create(
                    owner_record=record,
                    title=title,
                    defaults={
                        "document_type": document_type,
                        "state": Document.State.DRAFT,
                    },
                )
                if document.document_type != document_type:
                    document.document_type = document_type
                    document.save(update_fields=["document_type", "updated_at"])

                revision = _create_or_replace_revision(
                    document=document,
                    revision_label="A",
                    uploaded_file=generated_docx(title, body),
                    actor=actor,
                )
                revision.state = DocumentRevision.State.RELEASED
                revision.released_at = timezone.now()
                revision.save(update_fields=["state", "released_at", "updated_at"])
                document.current_revision = revision
                document.state = Document.State.RELEASED
                document.save(update_fields=["current_revision", "state", "updated_at"])
                note_document_link(record, title)
                record_audit_event(
                    actor,
                    "release.project_document_linked",
                    document,
                    before=None,
                    after=_document_snapshot(document),
                )

    def _prepare_workflow_tasks(self, actor, material_records):
        definition, _ = WorkflowDefinition.objects.update_or_create(
            key="client_material_review",
            version=1,
            defaults={
                "name": "Material Qualification Review",
                "object_type_key": "raw_material",
                "initial_state": "document_review",
                "is_active": True,
                "data": {"release_ready": True},
            },
        )
        task_specs = (
            ("pp", "Review PP technical data package", "Confirm TDS, SDS, and processing trial summary are linked."),
            ("rhdpe", "Approve recycled HDPE compliance package", "Review SDS and CAPA before supplier approval."),
            ("petg", "Confirm PETG processing guide release", "Validate PETG TDS links and processing-window summary."),
            ("pcabs", "Check PC/ABS weld-line experiment", "Review experiment summary before housing project release."),
        )
        tasks = []
        for key, title, description in task_specs:
            record = material_records[key]
            instance, _ = WorkflowInstance.objects.update_or_create(
                definition=definition,
                record=record,
                defaults={
                    "state": "document_review",
                    "data": {"release_ready": True},
                    "created_by": actor,
                    "updated_by": actor,
                },
            )
            task, _ = WorkflowTask.objects.update_or_create(
                instance=instance,
                title=title,
                defaults={
                    "key": f"material_review_{key}",
                    "description": description,
                    "assignee_user": actor,
                    "assignee_role": "Engineering",
                    "due_date": timezone.now() + timedelta(days=7),
                    "state": "open",
                    "required": True,
                    "related_record": record,
                    "created_by": actor,
                },
            )
            tasks.append(task)
        return tasks

    def _reset_audit_log(self):
        table = connection.ops.quote_name(AuditEvent._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {table}")

    def _delete_record_versions(self, record_ids):
        ids = [str(record_id) for record_id in record_ids]
        if not ids:
            return
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM records_recordversion WHERE record_id = ANY(%s::uuid[])", [ids])

    def _write_client_audit(self, actor, material_records, project_records):
        for record in list(material_records.values())[:8]:
            record_audit_event(
                actor,
                "release.material_prepared",
                record,
                before=None,
                after={"code": record.code, "title": record.title, "document_count": record.documents.count()},
            )
        for record in project_records:
            project = record.project
            record_audit_event(
                actor,
                "release.project_prepared",
                project,
                before=None,
                after={"name": project.name, "status": project.status, "record_id": str(record.pk)},
            )
        for document in Document.objects.select_related("owner_record").order_by("id")[:12]:
            record_audit_event(
                actor,
                "release.document_linked",
                document,
                before=None,
                after={"title": document.title, "owner_record": document.owner_record.code},
            )

    def _profile_key_for_document(self, title):
        value = title.lower()
        if "pc/abs" in value or "pc abs" in value or " alcom " in f" {value} " or "abs processing" in value or "abs " in value:
            return "pcabs"
        if "polycarbonate" in value or "p61" in value:
            return "pc"
        if "recycled" in value or "high density polyethylene" in value or "hdpe" in value:
            return "rhdpe"
        if "polypropylene" in value or value.startswith("pp-") or "pp high" in value or "ppc " in value:
            return "pp"
        if "nylon" in value or "polyamide" in value:
            return "nylon"
        if "delrin" in value or "acetal" in value or "pom" in value:
            return "pom"
        if "petg" in value:
            return "petg"
        if "tpu" in value or "polyurethane" in value:
            return "tpu"
        if "pvc" in value:
            return "pvc"
        if "acrylic" in value or "pmma" in value:
            return "pmma"
        if "pla " in value or value.startswith("pla"):
            return "pla"
        if "polystyrene" in value or "hips" in value:
            return "hips"
        if "qualification traceability matrix" in value:
            return "pp"
        raise CommandError(f"No material profile mapping for document title: {title}")

    def _curated_titles(self):
        return {source.title for source in SOURCE_DOCUMENTS} | {document.title for document in GENERATED_DOCUMENTS}

    def _is_noisy_record(self, record):
        text = f"{record.code} {record.title} {record.object_type_key} {record.data}".lower()
        return any(pattern in text for pattern in NOISE_PATTERNS)

    def _summary(self, index_counts, workflow_tasks):
        User = get_user_model()
        noisy_records = sum(1 for record in Record.objects.only("id", "code", "title", "object_type_key", "data") if self._is_noisy_record(record))
        noisy_documents = Document.objects.filter(title__icontains="qa").count() + Document.objects.filter(title__icontains="client-readiness").count()
        return (
            "Client release prepared: "
            f"active_users={User.objects.filter(is_active=True).count()}, "
            f"records={Record.objects.count()}, "
            f"documents={Document.objects.count()}, "
            f"projects={Project.objects.count()}, "
            f"open_workflow_tasks={len(workflow_tasks)}, "
            f"noisy_records={noisy_records}, "
            f"noisy_documents={noisy_documents}, "
            f"search_rebuild={index_counts}"
        )


def material_family_choice(profile: MaterialProfile):
    if profile.resin.upper() in {"HDPE"} and "recycled" in profile.title.lower():
        return "Regrind"
    if profile.resin.upper() in {"PVC"}:
        return "Other"
    return "Base Resin"


def reference_melt_flow_index(resin: str):
    values = {
        "PP": 12.5,
        "HDPE": 7.0,
        "PC": 10.0,
        "PC/ABS": 18.0,
        "PA66": 8.5,
        "POM": 9.0,
        "PETG": 6.0,
        "TPU": 4.5,
        "PVC": 3.0,
        "PMMA": 11.0,
        "PLA": 6.5,
        "HIPS": 5.0,
    }
    return values.get(resin.upper(), 8.0)


def reference_density(resin: str):
    values = {
        "PP": 0.9,
        "HDPE": 0.95,
        "PC": 1.2,
        "PC/ABS": 1.15,
        "PA66": 1.35,
        "POM": 1.41,
        "PETG": 1.27,
        "TPU": 1.18,
        "PVC": 1.38,
        "PMMA": 1.18,
        "PLA": 1.24,
        "HIPS": 1.04,
    }
    return values.get(resin.upper(), 1.0)


def sanitize_configuration_data(data):
    if not isinstance(data, dict):
        return data, False

    clean_data = deepcopy(data)
    removed_field_keys = set()
    changed = False

    for object_type in clean_data.get("object_types", []):
        fields = object_type.get("fields") or []
        clean_fields = []
        for field in fields:
            if is_noisy_config_field(field):
                removed_field_keys.add(field.get("key"))
                changed = True
            else:
                clean_fields.append(field)
        object_type["fields"] = clean_fields

    if removed_field_keys:
        for layout in clean_data.get("form_layouts", []):
            for section in layout.get("sections", []):
                fields = section.get("fields") or []
                clean_fields = [field for field in fields if field not in removed_field_keys]
                if clean_fields != fields:
                    section["fields"] = clean_fields
                    changed = True

    return clean_data, changed


def is_noisy_config_field(field):
    text = f"{field.get('key', '')} {field.get('label', '')}".lower()
    return any(
        token in text
        for token in (
            "qa_operator",
            "qa operator",
            "client_readiness",
            "client-readiness",
            "pw-rm",
            "pw_rm",
        )
    )

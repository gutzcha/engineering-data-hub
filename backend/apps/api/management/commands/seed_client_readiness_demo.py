import json
import os
import re
from hashlib import sha256
from datetime import timedelta
from ipaddress import ip_address
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from apps.accounts.models import ObjectPermission
from apps.accounts.permissions import CONFIGURATION_ADMIN_ROLE, SYSTEM_ADMIN_ROLE
from apps.config_registry.models import ConfigurationVersion
from apps.config_registry.services import create_draft_from_current, publish_draft
from apps.folders.models import FolderChangeEvent, ManagedFolder
from apps.folders.services import managed_path
from apps.projects.models import Project, ProjectBoardColumn, ProjectTask, ProjectTaskDependency
from apps.projects.services import create_project
from apps.records.models import Record
from apps.reports.models import Dashboard, DashboardWidget
from apps.search.tasks import enqueue_folder_event_indexes
from apps.workflows.models import WorkflowDefinition, WorkflowInstance, WorkflowTask


OBJECT_TYPES = ["product", "supplier", "raw_material", "product_spec", "project"]


class Command(BaseCommand):
    help = "Seed local-only client-readiness demo data for QA browser runs."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", default="", help="Run identifier used in seeded names.")
        parser.add_argument(
            "--manifest-path",
            default="",
            help="Optional path for writing a JSON manifest. The manifest is always printed.",
        )

    def handle(self, *args, **options):
        _require_safe_seed_target()
        run_id = options["run_id"] or timezone.now().strftime("client-readiness-%Y%m%d%H%M%S")
        run_slug = _run_slug(run_id)

        with override_settings(MANAGED_FOLDERS_AUTO_GENERATE=False):
            with transaction.atomic():
                actor = _seed_actor()
                _seed_permissions()
                active_config = _ensure_active_configuration(actor)
                manifest = _seed_operational_data(run_id, run_slug, actor, active_config)

        manifest_json = json.dumps(manifest, indent=2, sort_keys=True)
        manifest_path = options["manifest_path"]
        if manifest_path:
            path = Path(manifest_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(manifest_json, encoding="utf-8")

        self.stdout.write(manifest_json)


def _require_safe_seed_target():
    if os.environ.get("ALLOW_CLIENT_READINESS_SEED", "").lower() == "true":
        return
    if settings.DEBUG and _database_is_private():
        return
    raise CommandError(
        "Refusing to seed client-readiness data outside a local DEBUG target. "
        "Set ALLOW_CLIENT_READINESS_SEED=true only for an approved QA environment."
    )


def _database_is_private():
    database = settings.DATABASES.get("default", {})
    engine = database.get("ENGINE", "")
    if "sqlite" in engine:
        return True

    host = str(database.get("HOST") or "").strip()
    if not host:
        return True
    if host in {"localhost", "127.0.0.1", "::1", "db", "postgres", "backend", "host.docker.internal"}:
        return True

    try:
        parsed = ip_address(host)
    except ValueError:
        return False
    return parsed.is_loopback or parsed.is_private


def _run_slug(run_id):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", run_id).strip("-").upper()
    return (slug or "CLIENT-READINESS")[:36]


def _seed_actor():
    User = get_user_model()
    actor, _created = User.objects.update_or_create(
        username="client_readiness_seed",
        defaults={"is_active": True, "is_staff": True, "is_superuser": True},
    )
    actor.set_unusable_password()
    actor.save(update_fields=["password", "is_active", "is_staff", "is_superuser"])
    for role in [SYSTEM_ADMIN_ROLE, CONFIGURATION_ADMIN_ROLE, "Engineering", "Project Manager", "Product Admin"]:
        group, _created = Group.objects.get_or_create(name=role)
        actor.groups.add(group)
    return actor


def _seed_permissions():
    role_grants = {
        "Engineering": {
            "can_view": True,
            "can_create": True,
            "can_edit": True,
            "can_release": True,
            "can_admin": False,
        },
        "Project Manager": {
            "can_view": True,
            "can_create": True,
            "can_edit": True,
            "can_release": True,
            "can_admin": True,
        },
        "Product Admin": {
            "can_view": True,
            "can_create": True,
            "can_edit": True,
            "can_release": True,
            "can_admin": True,
        },
        CONFIGURATION_ADMIN_ROLE: {
            "can_view": True,
            "can_create": True,
            "can_edit": True,
            "can_release": True,
            "can_admin": True,
        },
        SYSTEM_ADMIN_ROLE: {
            "can_view": True,
            "can_create": True,
            "can_edit": True,
            "can_release": True,
            "can_admin": True,
        },
    }
    for role, grants in role_grants.items():
        Group.objects.get_or_create(name=role)
        for object_type in OBJECT_TYPES:
            ObjectPermission.objects.update_or_create(
                role_name=role,
                object_type_key=object_type,
                defaults=grants,
            )


def _ensure_active_configuration(actor):
    active_config = ConfigurationVersion.objects.order_by("-version").first()
    if active_config:
        return active_config
    return publish_draft(create_draft_from_current(actor), actor)


def _seed_operational_data(run_id, run_slug, actor, active_config):
    product = _seed_product_record(run_slug, actor, active_config)
    projects = _seed_projects(run_slug, actor)
    workflow_tasks = _seed_workflow_tasks(run_slug, actor, product)
    managed_folder, folder_events = _seed_folder_events(run_slug, product, actor)
    dashboard = _seed_dashboard(run_slug)

    return {
        "runId": run_id,
        "actor": actor.username,
        "activeConfigVersion": active_config.version,
        "records": {
            "productRecordId": str(product.pk),
            "projectRecordIds": [str(project.record_id) for project in projects],
        },
        "projects": [
            {"id": str(project.pk), "recordId": str(project.record_id), "name": project.name}
            for project in projects
        ],
        "projectTasks": [
            {"id": task.pk, "projectId": str(task.project_id), "title": task.title, "state": task.state}
            for project in projects
            for task in project.tasks.all()
        ],
        "workflowTasks": [
            {"id": task.pk, "title": task.title, "state": task.state, "relatedRecordId": str(product.pk)}
            for task in workflow_tasks
        ],
        "managedFolders": [
            {
                "id": managed_folder.pk,
                "recordId": str(product.pk),
                "relativePath": managed_folder.relative_path,
            }
        ],
        "folderEvents": [
            {"id": event.pk, "path": event.path, "reviewStatus": event.review_status}
            for event in folder_events
        ],
        "dashboardKey": dashboard.config.get("key"),
    }


def _seed_product_record(run_slug, actor, active_config):
    code = f"QA-SEED-PROD-{run_slug}"
    record, _created = Record.objects.get_or_create(
        code=code,
        defaults={
            "object_type_key": "product",
            "title": f"QA Client Readiness Product {run_slug}",
            "schema_version": active_config.version,
            "data": {
                "commercial_name": f"QA Client Readiness Product {run_slug}",
                "internal_grade": f"QA-{run_slug}",
                "resin_family": "PC",
                "application": "Transparent machine guard",
                "color": "Clear",
            },
            "created_by": actor,
            "updated_by": actor,
        },
    )
    return record


def _seed_projects(run_slug, actor):
    project_specs = [
        ("Tooling Transfer", "Transfer mold qualification to the production tool room."),
        ("Regrind Qualification", "Qualify 15 percent PC regrind in a visible part."),
        ("Supplier Change", "Approve alternate ABS resin supplier."),
        ("Document Cleanup", "Bring controlled plastic data sheets into release state."),
    ]
    projects = []
    for index, (name, description) in enumerate(project_specs, start=1):
        project_name = f"QA {name} {run_slug}"
        project = Project.objects.filter(name=project_name).first()
        if project is None:
            project = create_project(
                name=project_name,
                actor=actor,
                description=description,
                data={"project_type": "Material Change"},
            )
        columns = _seed_project_columns(project)
        _seed_project_tasks(project, columns, actor, index)
        projects.append(project)
    return projects


def _seed_project_columns(project):
    return {
        key: ProjectBoardColumn.objects.get_or_create(
            project=project,
            key=key,
            defaults={"title": title, "sort_order": order},
        )[0]
        for key, title, order in [
            ("todo", "To Do", 1),
            ("doing", "Doing", 2),
            ("done", "Done", 3),
            ("blocked", "Blocked", 4),
        ]
    }


def _seed_project_tasks(project, columns, actor, project_index):
    today = timezone.localdate()
    task_specs = [
        ("Review resin data sheet", "todo", ProjectTask.State.TODO, today + timedelta(days=2), 1),
        ("Run first article molding pass", "doing", ProjectTask.State.IN_PROGRESS, today + timedelta(days=5), 2),
        ("Resolve supplier discrepancy", "blocked", ProjectTask.State.BLOCKED, today - timedelta(days=1), 3),
        ("Archive superseded document set", "done", ProjectTask.State.DONE, today - timedelta(days=3), 4),
    ]
    tasks = []
    for title, column_key, state, due_date, sort_order in task_specs:
        task, _created = ProjectTask.objects.get_or_create(
            project=project,
            title=f"QA {project_index} {title}",
            defaults={
                "column": columns[column_key],
                "state": state,
                "assignee_user": actor,
                "assignee_role": "Engineering",
                "due_date": due_date,
                "estimated_hours": 2 + sort_order,
                "sort_order": sort_order,
                "created_by": actor,
                "updated_by": actor,
            },
        )
        tasks.append(task)
    ProjectTaskDependency.objects.get_or_create(task=tasks[1], depends_on=tasks[0], defaults={"created_by": actor})


def _seed_workflow_tasks(run_slug, actor, product):
    definition, _created = WorkflowDefinition.objects.get_or_create(
        key=f"qa_client_readiness_{run_slug.lower()}",
        defaults={
            "name": f"QA Client Readiness Workflow {run_slug}",
            "object_type_key": "product",
            "initial_state": "draft",
            "version": 1,
            "is_active": True,
        },
    )
    instance, _created = WorkflowInstance.objects.get_or_create(
        definition=definition,
        record=product,
        defaults={"state": "draft", "created_by": actor, "updated_by": actor},
    )
    now = timezone.now()
    task_specs = [
        ("review_material_data", "Review material data", now - timedelta(days=2), "Engineering"),
        ("approve_supplier", "Approve supplier dossier", now + timedelta(days=2), "Quality"),
        ("release_document", "Release controlled document", now + timedelta(days=5), "Approver"),
        ("check_regrind", "Check regrind declaration", now - timedelta(days=1), "Engineering"),
    ]
    tasks = []
    for key, title, due_date, role in task_specs:
        task, _created = WorkflowTask.objects.get_or_create(
            instance=instance,
            key=key,
            defaults={
                "title": f"QA {title} {run_slug}",
                "assignee_user": actor,
                "assignee_role": role,
                "due_date": due_date,
                "state": WorkflowTask.State.OPEN,
                "related_record": product,
                "created_by": actor,
            },
        )
        tasks.append(task)
    return tasks


def _seed_folder_events(run_slug, product, actor):
    folder_relative_path = f"QA/{run_slug}/ProductDocs"
    managed_folder, _created = ManagedFolder.objects.update_or_create(
        record=product,
        folder_role="primary",
        defaults={
            "absolute_path": str(managed_path(folder_relative_path)),
            "relative_path": folder_relative_path,
            "template_key": "product_standard",
            "state": ManagedFolder.State.ACTIVE,
        },
    )
    event_specs = [
        (FolderChangeEvent.EventType.ADDED, "PC_TDS.pdf", FolderChangeEvent.ReviewStatus.PENDING),
        (FolderChangeEvent.EventType.MODIFIED, "ABS_COA.pdf", FolderChangeEvent.ReviewStatus.PENDING),
        (FolderChangeEvent.EventType.COLLISION, "duplicate_spec.pdf", FolderChangeEvent.ReviewStatus.PENDING),
        (FolderChangeEvent.EventType.LINK_REQUESTED, "supplier_letter.pdf", FolderChangeEvent.ReviewStatus.PENDING),
        (FolderChangeEvent.EventType.ADDED, "accepted_pp_sheet.pdf", FolderChangeEvent.ReviewStatus.ACCEPTED),
        (FolderChangeEvent.EventType.MODIFIED, "ignored_legacy_sheet.pdf", FolderChangeEvent.ReviewStatus.IGNORED),
    ]
    events = []
    for event_type, filename, status in event_specs:
        event, _created = FolderChangeEvent.objects.get_or_create(
            managed_folder=managed_folder,
            path=f"{managed_folder.relative_path}/{filename}",
            event_type=event_type,
            defaults={
                "detected_hash": sha256(f"{run_slug}/{filename}".encode()).hexdigest(),
                "matched_record": product,
                "review_status": status,
                "reviewer": actor if status != FolderChangeEvent.ReviewStatus.PENDING else None,
                "assigned_to": actor,
            },
        )
        events.append(event)
    enqueue_folder_event_indexes([event.pk for event in events])
    return managed_folder, events


def _seed_dashboard(run_slug):
    dashboard, _created = Dashboard.objects.get_or_create(
        name=f"QA Client Readiness Dashboard {run_slug}",
        defaults={
            "description": "Seeded operational dashboard for client-readiness QA.",
            "config": {"key": f"qa_client_readiness_{run_slug.lower()}"},
        },
    )
    DashboardWidget.objects.get_or_create(
        dashboard=dashboard,
        title="QA Records by Status",
        defaults={
            "widget_type": DashboardWidget.WidgetType.COUNT_BY_STATUS,
            "config": {},
            "sort_order": 1,
        },
    )
    DashboardWidget.objects.get_or_create(
        dashboard=dashboard,
        title="QA Overdue Project Tasks",
        defaults={
            "widget_type": DashboardWidget.WidgetType.OVERDUE_PROJECT_TASKS,
            "config": {},
            "sort_order": 2,
        },
    )
    return dashboard

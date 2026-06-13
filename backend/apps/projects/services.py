# ===
# File Summary
# Path: backend\apps\projects\services.py
# Type: python
# Purpose: Projects domain for entity lifecycle and dependency graph orchestration.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: create_project, move_task, add_task_dependency, _lock_project_dependency_graph, _would_create_cycle
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

from types import SimpleNamespace

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.permissions import user_can
from apps.audit.services import record_audit_event, snapshot_model
from apps.projects.models import (
    Project,
    ProjectBoardColumn,
    ProjectEvent,
    ProjectTask,
    ProjectTaskDependency,
)
from apps.records.serializers import RecordSerializer
from apps.search.tasks import enqueue_record_index


@transaction.atomic
def create_project(
    *,
    name: str,
    actor,
    description: str = "",
    start_date=None,
    target_date=None,
    owner=None,
    data: dict | None = None,
) -> Project:
    if not user_can(actor, "create", "project"):
        raise PermissionDenied("You do not have permission to create projects.")

    record_data = {}
    if data:
        record_data.update(data)
    record_data["project_name"] = name
    record_data.setdefault("project_type", "New Product")

    serializer = RecordSerializer(
        data={"object_type_key": "project", "data": record_data},
        context={"request": SimpleNamespace(user=actor)},
    )
    serializer.is_valid(raise_exception=True)
    record = serializer.save()
    enqueue_record_index(record.pk)
    project = Project.objects.create(
        record=record,
        name=name,
        description=description,
        start_date=start_date,
        target_date=target_date,
        owner=owner or actor,
        created_by=actor,
        updated_by=actor,
    )
    record_audit_event(
        actor,
        "project.created",
        project,
        before=None,
        after=_project_snapshot(project),
    )
    return project


@transaction.atomic
def move_task(
    *,
    task: ProjectTask,
    column_id: int | None,
    sort_order: int,
    actor,
    request=None,
) -> ProjectTask:
    if sort_order < 0:
        raise ValidationError({"sort_order": ["Must be greater than or equal to 0."]})

    task = (
        ProjectTask.objects.select_for_update()
        .select_related("project__record", "column")
        .get(pk=task.pk)
    )
    if not user_can(actor, "edit", "project", record_id=str(task.project.record_id)):
        raise PermissionDenied("You do not have permission to edit this project.")

    old_column_id = task.column_id
    old_sort_order = task.sort_order
    before = _project_task_snapshot(task)
    column = None
    if column_id is not None:
        try:
            column = ProjectBoardColumn.objects.get(pk=column_id, project=task.project)
        except ProjectBoardColumn.DoesNotExist as error:
            raise ValidationError({"column": ["Column was not found in this project."]}) from error

    task.column = column
    task.sort_order = sort_order
    task.updated_by = actor
    task.save(update_fields=["column", "sort_order", "updated_by", "updated_at"])
    ProjectEvent.objects.create(
        project=task.project,
        task=task,
        action="task_moved",
        actor=actor,
        data={
            "from_column": old_column_id,
            "to_column": task.column_id,
            "from_sort_order": old_sort_order,
            "to_sort_order": task.sort_order,
        },
    )
    record_audit_event(
        actor,
        "project.task_moved",
        task,
        before=before,
        after=_project_task_snapshot(task),
        request=request,
    )
    return task


@transaction.atomic
def add_task_dependency(
    *,
    task: ProjectTask,
    depends_on_id: int,
    actor,
    request=None,
) -> ProjectTaskDependency:
    project = _lock_project_dependency_graph(task.project_id)
    task = ProjectTask.objects.select_for_update().select_related("project__record").get(
        pk=task.pk,
        project=project,
    )
    if not user_can(actor, "edit", "project", record_id=str(task.project.record_id)):
        raise PermissionDenied("You do not have permission to edit this project.")
    if task.pk == depends_on_id:
        raise ValidationError({"detail": "A task cannot depend on itself."})

    try:
        depends_on = ProjectTask.objects.get(pk=depends_on_id, project=task.project)
    except ProjectTask.DoesNotExist as error:
        raise ValidationError({"depends_on": ["Dependency task was not found in this project."]}) from error

    if _would_create_cycle(task=task, depends_on=depends_on):
        raise ValidationError({"detail": "Circular task dependencies are not allowed."})

    dependency, _created = ProjectTaskDependency.objects.get_or_create(
        task=task,
        depends_on=depends_on,
        defaults={"created_by": actor},
    )
    if _created:
        record_audit_event(
            actor,
            "project.dependency_created",
            dependency,
            before=None,
            after=snapshot_model(dependency, ["id", "task_id", "depends_on_id", "created_by_id"]),
            request=request,
        )
    return dependency


def _lock_project_dependency_graph(project_id):
    project = Project.objects.select_for_update().select_related("record").get(pk=project_id)
    list(
        ProjectTask.objects.select_for_update()
        .filter(project=project)
        .order_by("id")
        .values_list("id", flat=True)
    )
    list(
        ProjectTaskDependency.objects.select_for_update()
        .filter(task__project=project, depends_on__project=project)
        .order_by("id")
        .values_list("id", flat=True)
    )
    return project


def _would_create_cycle(*, task: ProjectTask, depends_on: ProjectTask) -> bool:
    pending = [depends_on.pk]
    visited = set()
    while pending:
        current_id = pending.pop()
        if current_id == task.pk:
            return True
        if current_id in visited:
            continue
        visited.add(current_id)
        pending.extend(
            ProjectTaskDependency.objects.filter(task_id=current_id).values_list(
                "depends_on_id",
                flat=True,
            )
        )
    return False


def _project_snapshot(project):
    return snapshot_model(
        project,
        [
            "id",
            "record_id",
            "name",
            "description",
            "status",
            "start_date",
            "target_date",
            "owner_id",
            "created_by_id",
            "updated_by_id",
        ],
    )


def _project_task_snapshot(task):
    return snapshot_model(
        task,
        [
            "id",
            "project_id",
            "column_id",
            "milestone_id",
            "title",
            "state",
            "assignee_user_id",
            "assignee_role",
            "start_date",
            "due_date",
            "estimated_hours",
            "sort_order",
            "completed_at",
        ],
    )


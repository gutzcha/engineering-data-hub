# ===
# File Summary
# Path: backend\apps\projects\views.py
# Type: python
# Purpose: Projects domain for entity lifecycle and dependency graph orchestration.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: IsAuthenticated, has_permission, ProjectBoardView, get, ProjectTaskMoveView
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

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import records_user_can_view, user_has_view_scope, user_can
from apps.projects.models import (
    Project,
    ProjectEvent,
    ProjectTask,
    ProjectTaskDependency,
)
from apps.projects.serializers import (
    ProjectListSerializer,
    ProjectTaskDependencySerializer,
    ProjectTaskSerializer,
)
from apps.projects.services import add_task_dependency, move_task
from apps.records.models import Record


def models_filter_query(query):
    from django.db.models import Q

    return (
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(record__code__icontains=query)
        | Q(record__title__icontains=query)
    )


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class ProjectListView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        queryset = Project.objects.select_related("record").all()
        visible_project_record_ids = records_user_can_view(
            request.user,
            Record.objects.filter(object_type_key="project"),
        ).values_list("pk", flat=True)
        queryset = queryset.filter(record_id__in=visible_project_record_ids)

        query = (request.query_params.get("q") or "").strip()
        status_filter = (request.query_params.get("status") or "").strip()
        record_filter = (request.query_params.get("record") or "").strip()
        if query:
            queryset = queryset.filter(
                models_filter_query(query),
            )
        if status_filter:
            queryset = queryset.filter(status__in=_split_csv(status_filter))
        if record_filter:
            queryset = queryset.filter(record_id__iexact=record_filter)

        return Response(ProjectListSerializer(queryset, many=True).data, status=status.HTTP_200_OK)


class ProjectBoardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(request.user, project_id, "view")
        tasks_by_column = {}
        tasks = project.tasks.select_related("column", "assignee_user").order_by(
            "sort_order",
            "created_at",
            "id",
        )
        for task in tasks:
            tasks_by_column.setdefault(task.column_id, []).append(_serialize_board_task(task))

        return Response(
            {
                "project": _serialize_project(project),
                "columns": [
                    {
                        "id": column.pk,
                        "key": column.key,
                        "title": column.title,
                        "sort_order": column.sort_order,
                        "wip_limit": column.wip_limit,
                        "tasks": tasks_by_column.get(column.pk, []),
                    }
                    for column in project.board_columns.all().order_by("sort_order", "id")
                ],
                "unassigned_tasks": tasks_by_column.get(None, []),
            },
            status=status.HTTP_200_OK,
        )


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(request.user, project_id, "view")
        return Response(
            {
                "project": _serialize_project(project),
                "record": {
                    "id": str(project.record_id),
                    "code": project.record.code,
                    "title": project.record.title,
                    "status": project.record.status,
                    "object_type_key": project.record.object_type_key,
                    "data": project.record.data,
                },
                "milestones": [
                    {
                        "id": milestone.pk,
                        "title": milestone.title,
                        "target_date": milestone.target_date.isoformat()
                        if milestone.target_date
                        else None,
                        "completed_at": milestone.completed_at.isoformat()
                        if milestone.completed_at
                        else None,
                        "sort_order": milestone.sort_order,
                    }
                    for milestone in project.milestones.all().order_by(
                        "target_date",
                        "sort_order",
                        "id",
                    )
                ],
                "tasks": [
                    _serialize_board_task(task)
                    for task in project.tasks.select_related(
                        "column",
                        "milestone",
                        "assignee_user",
                    ).order_by("sort_order", "created_at", "id")
                ],
            },
            status=status.HTTP_200_OK,
        )


class ProjectEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(request.user, project_id, "view")
        events = ProjectEvent.objects.filter(project=project).select_related("task", "actor")
        return Response(
            [
                {
                    "id": event.pk,
                    "project": str(event.project_id),
                    "task": event.task_id,
                    "task_title": event.task.title if event.task_id else "",
                    "action": event.action,
                    "actor": event.actor_id,
                    "actor_username": event.actor.username if event.actor_id else "",
                    "comment": event.comment,
                    "data": event.data,
                    "created_at": event.created_at.isoformat(),
                }
                for event in events.order_by("-created_at", "-id")
            ],
            status=status.HTTP_200_OK,
        )


class ProjectTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        task = get_object_or_404(
            ProjectTask.objects.select_related(
                "project__record",
                "column",
                "milestone",
                "assignee_user",
            ),
            pk=pk,
        )
        if not user_can(request.user, "view", "project", record_id=str(task.project.record_id)):
            raise PermissionDenied("You do not have permission to view this project task.")
        return Response(ProjectTaskSerializer(task).data, status=status.HTTP_200_OK)


class ProjectTaskMoveView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        task = get_object_or_404(ProjectTask.objects.select_related("project__record"), pk=pk)
        column_id = _optional_int(request.data.get("column"), "column")
        if "sort_order" not in request.data:
            raise ValidationError({"sort_order": ["This field is required."]})
        sort_order = _required_int(request.data["sort_order"], "sort_order")
        if sort_order < 0:
            raise ValidationError({"sort_order": ["Must be greater than or equal to 0."]})
        moved = move_task(
            task=task,
            column_id=column_id,
            sort_order=sort_order,
            actor=request.user,
            request=request,
        )
        return Response(ProjectTaskSerializer(moved).data, status=status.HTTP_200_OK)


class ProjectTimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(request.user, project_id, "view")
        milestones = [
            {
                "id": milestone.pk,
                "title": milestone.title,
                "target_date": milestone.target_date.isoformat()
                if milestone.target_date
                else None,
                "completed_at": milestone.completed_at.isoformat()
                if milestone.completed_at
                else None,
            }
            for milestone in project.milestones.all().order_by("target_date", "sort_order", "id")
        ]
        tasks = [
            {
                "id": task.pk,
                "title": task.title,
                "state": task.state,
                "start_date": task.start_date.isoformat() if task.start_date else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "milestone": task.milestone_id,
                "assignee_user": task.assignee_user_id,
                "estimated_hours": task.estimated_hours,
            }
            for task in project.tasks.all().order_by("start_date", "due_date", "sort_order", "id")
        ]
        dependencies = [
            {"task": dependency.task_id, "depends_on": dependency.depends_on_id}
            for dependency in ProjectTaskDependency.objects.filter(
                task__project=project,
                depends_on__project=project,
            ).order_by("task_id", "depends_on_id")
        ]
        return Response(
            {
                "project": _serialize_project(project),
                "milestones": milestones,
                "tasks": tasks,
                "dependencies": dependencies,
            },
            status=status.HTTP_200_OK,
        )


class ProjectTaskDependencyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        task = get_object_or_404(ProjectTask.objects.select_related("project__record"), pk=pk)
        if "depends_on" not in request.data:
            raise ValidationError({"depends_on": ["This field is required."]})
        dependency = add_task_dependency(
            task=task,
            depends_on_id=_required_int(request.data["depends_on"], "depends_on"),
            actor=request.user,
            request=request,
        )
        return Response(
            ProjectTaskDependencySerializer(dependency).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectWorkloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not user_has_view_scope(request.user, "project"):
            raise PermissionDenied("You do not have permission to view projects.")
        visible_project_record_ids = records_user_can_view(
            request.user,
            Record.objects.filter(object_type_key="project"),
        ).values_list("pk", flat=True)
        rows = (
            ProjectTask.objects.exclude(state=ProjectTask.State.DONE)
            .exclude(assignee_user__isnull=True)
            .select_related("project__record")
            .filter(project__record__object_type_key="project")
            .filter(project__record_id__in=visible_project_record_ids)
            .values("assignee_user", "assignee_user__username")
            .annotate(
                open_tasks=Count("id"),
                estimated_hours=Coalesce(Sum("estimated_hours"), 0.0),
            )
            .order_by("assignee_user__username", "assignee_user")
        )
        return Response(
            [
                {
                    "assignee_user": row["assignee_user"],
                    "username": row["assignee_user__username"],
                    "open_tasks": row["open_tasks"],
                    "estimated_hours": float(row["estimated_hours"]),
                }
                for row in rows
            ],
            status=status.HTTP_200_OK,
        )


def _get_project(user, project_id, action):
    project = get_object_or_404(Project.objects.select_related("record"), pk=project_id)
    if not user_can(user, action, "project", record_id=str(project.record_id)):
        raise PermissionDenied(f"You do not have permission to {action} this project.")
    return project


def _serialize_project(project):
    return {
        "id": str(project.pk),
        "record": str(project.record_id),
        "record_code": project.record.code,
        "name": project.name,
        "status": project.status,
    }


def _serialize_board_task(task):
    return {
        "id": task.pk,
        "title": task.title,
        "state": task.state,
        "column": task.column_id,
        "milestone": task.milestone_id,
        "assignee_user": task.assignee_user_id,
        "estimated_hours": task.estimated_hours,
        "sort_order": task.sort_order,
    }


def _optional_int(value, field_name):
    if value is None or value == "":
        return None
    return _required_int(value, field_name)


def _required_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError({field_name: ["Expected an integer."]}) from error


def _split_csv(raw):
    return [value.strip().lower() for value in raw.split(",") if value.strip()]


from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import records_user_can_view, user_has_view_scope, user_can
from apps.audit.services import record_audit_event, snapshot_model
from apps.projects.models import (
    Project,
    ProjectEvent,
    ProjectTask,
    ProjectTaskDependency,
)
from apps.projects.serializers import (
    ProjectCreateSerializer,
    ProjectEventSerializer,
    ProjectSerializer,
    ProjectTaskDependencySerializer,
    ProjectTaskSerializer,
    ProjectTaskUpdateSerializer,
    ProjectUpdateSerializer,
)
from apps.projects.services import add_task_dependency, create_project, move_task, update_project
from apps.records.models import Record


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


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


class ProjectTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        task = get_object_or_404(ProjectTask.objects.select_related("project__record"), pk=pk)
        if not user_can(request.user, "edit", "project", record_id=str(task.project.record_id)):
            raise PermissionDenied("You do not have permission to edit this project task.")
        serializer = ProjectTaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        before = _project_task_audit_snapshot(task)
        update_fields = []
        for field, value in serializer.validated_data.items():
            setattr(task, field, value)
            update_fields.append(field)
        task.updated_by = request.user
        update_fields.extend(["updated_by", "updated_at"])
        task.save(update_fields=update_fields)
        ProjectEvent.objects.create(
            project=task.project,
            task=task,
            action="task_updated",
            actor=request.user,
            data={"fields": list(serializer.validated_data.keys())},
        )
        record_audit_event(
            request.user,
            "project.task_updated",
            task,
            before=before,
            after=_project_task_audit_snapshot(task),
            request=request,
        )
        return Response(ProjectTaskSerializer(task).data, status=status.HTTP_200_OK)


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


class ProjectListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not user_has_view_scope(request.user, "project"):
            raise PermissionDenied("You do not have permission to view projects.")
        visible_project_record_ids = records_user_can_view(
            request.user,
            Record.objects.filter(object_type_key="project"),
        ).values_list("pk", flat=True)
        projects = (
            Project.objects.select_related("record", "owner")
            .filter(record_id__in=visible_project_record_ids)
            .annotate(
                task_count=Count("tasks", distinct=True),
                open_tasks=Count(
                    "tasks",
                    filter=~Q(tasks__state=ProjectTask.State.DONE),
                    distinct=True,
                ),
            )
            .order_by("-updated_at", "name")
        )
        return Response(
            [
                {
                    **_serialize_project(project),
                    "description": project.description,
                    "owner": project.owner.username if project.owner else None,
                    "start_date": project.start_date.isoformat() if project.start_date else None,
                    "target_date": project.target_date.isoformat() if project.target_date else None,
                    "task_count": project.task_count,
                    "open_tasks": project.open_tasks,
                    "updated_at": project.updated_at.isoformat(),
                }
                for project in projects
            ],
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = create_project(
            name=serializer.validated_data["name"],
            actor=request.user,
            description=serializer.validated_data.get("description", ""),
            start_date=serializer.validated_data.get("start_date"),
            target_date=serializer.validated_data.get("target_date"),
            owner=serializer.validated_data.get("owner"),
            data=serializer.validated_data.get("data"),
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(request.user, project_id, "view")
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)

    def patch(self, request, project_id):
        project = _get_project(request.user, project_id, "edit")
        serializer = ProjectUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_project = update_project(
            project=project,
            actor=request.user,
            request=request,
            **serializer.validated_data,
        )
        return Response(ProjectSerializer(updated_project).data, status=status.HTTP_200_OK)


class ProjectEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(request.user, project_id, "view")
        events = project.events.select_related("actor", "task").order_by("-created_at", "-id")[:100]
        return Response(ProjectEventSerializer(events, many=True).data, status=status.HTTP_200_OK)


def _get_project(user, project_id, action):
    project = get_object_or_404(Project.objects.select_related("record"), pk=project_id)
    if not user_can(user, action, "project", record_id=str(project.record_id)):
        raise PermissionDenied(f"You do not have permission to {action} this project.")
    return project


def _serialize_project(project):
    return {
        "id": str(project.pk),
        "record": str(project.record_id),
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


def _project_audit_snapshot(project):
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
            "updated_by_id",
        ],
    )


def _project_task_audit_snapshot(task):
    return snapshot_model(
        task,
        [
            "id",
            "project_id",
            "column_id",
            "title",
            "state",
            "assignee_user_id",
            "due_date",
            "estimated_hours",
            "updated_by_id",
        ],
    )


def _optional_int(value, field_name):
    if value is None or value == "":
        return None
    return _required_int(value, field_name)


def _required_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError({field_name: ["Expected an integer."]}) from error

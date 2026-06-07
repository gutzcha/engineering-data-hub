from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE, user_can
from apps.records.models import Record
from apps.workflows.engine import (
    WorkflowGuardError,
    WorkflowTransitionError,
    available_transitions,
    get_or_create_instance_for_record,
    perform_transition,
)
from apps.workflows.models import WorkflowTask, WorkflowTaskStateError, WorkflowTransition


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class WorkflowTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTask
        fields = [
            "id",
            "key",
            "instance",
            "title",
            "description",
            "assignee_user",
            "assignee_role",
            "due_date",
            "state",
            "required",
            "related_record",
            "related_document",
            "related_project",
            "completed_by",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WorkflowTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = _visible_tasks_for_user(request.user)
        state_filter = request.query_params.get("state")
        if state_filter:
            tasks = tasks.filter(state=state_filter)
        return Response(WorkflowTaskSerializer(tasks, many=True).data, status=status.HTTP_200_OK)


class WorkflowTaskCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        with transaction.atomic():
            task = get_object_or_404(
                WorkflowTask.objects.select_for_update().select_related("instance__record"),
                pk=pk,
            )
            record = task.related_record or task.instance.record
            if not user_can(request.user, "view", record.object_type_key, record_id=str(record.pk)):
                raise PermissionDenied("You do not have permission to view this task.")
            if not _can_complete_task(request.user, task):
                raise PermissionDenied("You do not have permission to complete this task.")
            try:
                task.mark_done(request.user, request.data.get("comment", ""), request=request)
            except WorkflowTaskStateError as error:
                return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(WorkflowTaskSerializer(task).data, status=status.HTTP_200_OK)


class RecordWorkflowView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, record_id):
        record = _get_visible_record(request.user, record_id)
        instance = get_or_create_instance_for_record(record, request.user)
        if instance is None:
            return Response({"detail": "No active workflow for this record."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_instance(instance), status=status.HTTP_200_OK)


class RecordWorkflowTransitionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, record_id, transition_key):
        record = _get_visible_record(request.user, record_id)
        instance = get_or_create_instance_for_record(record, request.user)
        if instance is None:
            return Response({"detail": "No active workflow for this record."}, status=status.HTTP_404_NOT_FOUND)
        transition = get_object_or_404(
            WorkflowTransition,
            definition=instance.definition,
            key=transition_key,
            from_state=instance.state,
        )
        _require_transition_permission(request.user, record, transition)
        try:
            instance = perform_transition(
                str(instance.pk),
                transition_key,
                request.user.pk,
                request.data.get("comment", ""),
                request=request,
            )
        except WorkflowGuardError as error:
            return Response({"detail": str(error), "errors": error.errors}, status=status.HTTP_400_BAD_REQUEST)
        except WorkflowTransitionError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_instance(instance), status=status.HTTP_200_OK)


def _visible_tasks_for_user(user):
    if user.is_superuser or user.groups.filter(name=SYSTEM_ADMIN_ROLE).exists():
        tasks = WorkflowTask.objects.all()
    else:
        roles = list(user.groups.values_list("name", flat=True))
        tasks = WorkflowTask.objects.filter(Q(assignee_user=user) | Q(assignee_role__in=roles))
    visible_ids = [
        task.pk
        for task in tasks.select_related("related_record", "instance__record")
        if user_can(
            user,
            "view",
            (task.related_record or task.instance.record).object_type_key,
            record_id=str((task.related_record or task.instance.record).pk),
        )
    ]
    return WorkflowTask.objects.filter(pk__in=visible_ids).select_related(
        "assignee_user",
        "related_record",
        "related_document",
    )


def _can_complete_task(user, task):
    if user.is_superuser or user.groups.filter(name=SYSTEM_ADMIN_ROLE).exists():
        return True
    if task.assignee_user_id == user.pk:
        return True
    return bool(task.assignee_role and user.groups.filter(name=task.assignee_role).exists())


def _get_visible_record(user, record_id):
    record = get_object_or_404(Record, pk=record_id)
    if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
        raise PermissionDenied("You do not have permission to view this record.")
    return record


def _require_transition_permission(user, record, transition):
    guards = transition.guards or {}
    required_permission = guards.get("required_permission")
    required_permissions = guards.get("required_permissions")
    if required_permission:
        action = required_permission
    elif isinstance(required_permissions, list) and required_permissions:
        action = required_permissions[0]
    else:
        action = "edit"
    if not user_can(user, action, record.object_type_key, record_id=str(record.pk)):
        raise PermissionDenied(f"You do not have permission to {action} this record.")


def _serialize_instance(instance):
    instance.refresh_from_db()
    tasks = instance.tasks.select_related("assignee_user", "related_record", "related_document")
    transitions = available_transitions(instance)
    return {
        "id": str(instance.pk),
        "definition": instance.definition.key,
        "record": str(instance.record_id),
        "state": instance.state,
        "tasks": WorkflowTaskSerializer(tasks, many=True).data,
        "available_transitions": [
            {
                "key": transition.key,
                "label": transition.label,
                "to_state": transition.to_state,
            }
            for transition in transitions
        ],
    }

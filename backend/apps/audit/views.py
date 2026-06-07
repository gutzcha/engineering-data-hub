from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE, user_can
from apps.audit.models import AuditEvent
from apps.documents.models import Document
from apps.records.models import Record


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class AuditEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "actor",
            "actor_username",
            "action",
            "object_type",
            "object_id",
            "before",
            "after",
            "request_id",
            "ip_address",
            "user_agent",
            "created_at",
        ]
        read_only_fields = fields


class AuditEventListView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        events = _visible_events(
            request.user,
            _filtered_queryset(request),
            limit=_result_limit(request),
        )
        return audit_response(events)


class RecordAuditView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        record = get_object_or_404(Record, pk=pk)
        if not user_can(request.user, "view", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to view this record.")
        return audit_response(record_audit_events(record))


class DocumentAuditView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        document = get_object_or_404(Document.objects.select_related("owner_record"), pk=pk)
        if not user_can(
            request.user,
            "view",
            document.owner_record.object_type_key,
            record_id=str(document.owner_record_id),
        ):
            raise PermissionDenied("You do not have permission to view this document.")
        return audit_response(document_audit_events(document))


def audit_response(events, *, status_code=status.HTTP_200_OK):
    serializer = AuditEventSerializer(events, many=True)
    return Response({"results": serializer.data}, status=status_code)


def record_audit_events(record):
    return AuditEvent.objects.filter(object_type="record", object_id=str(record.pk)).select_related(
        "actor"
    )


def document_audit_events(document):
    return AuditEvent.objects.filter(
        object_type="document",
        object_id=str(document.pk),
    ).select_related("actor")


def _filtered_queryset(request):
    queryset = AuditEvent.objects.select_related("actor")
    for field in ("action", "object_type", "object_id", "request_id"):
        value = request.query_params.get(field)
        if value:
            queryset = queryset.filter(**{field: value})
    return queryset


def _visible_events(user, queryset, *, limit=100):
    if _is_system_admin(user):
        return queryset[:limit]

    visible_events = []
    for event in queryset.iterator(chunk_size=200):
        if _event_is_visible(user, event):
            visible_events.append(event)
            if len(visible_events) >= limit:
                break
    return visible_events


def _result_limit(request):
    try:
        requested_limit = int(request.query_params.get("limit", 100))
    except (TypeError, ValueError):
        return 100
    return max(1, min(requested_limit, 500))


def _event_is_visible(user, event):
    if not user or isinstance(user, AnonymousUser):
        return False
    if event.object_type == "record":
        return _can_view_record_event(user, event.object_id)
    if event.object_type == "document":
        return _can_view_document_event(user, event.object_id)
    payload = event.after if isinstance(event.after, dict) else event.before
    if not isinstance(payload, dict):
        return False
    object_type_key = _object_type_key_from_payload(payload)
    if object_type_key:
        return user_can(user, "view", object_type_key)
    record_id = _record_id_from_payload(payload)
    if record_id:
        return _can_view_record_event(user, record_id)
    if event.object_type == "project":
        return _can_view_project_event(user, event.object_id)
    if event.object_type == "projecttask":
        return _can_view_project_event(user, payload.get("project_id"))
    if event.object_type == "projecttaskdependency":
        return _can_view_project_task_event(user, payload.get("task_id"))
    if event.object_type == "workflowinstance":
        return _can_view_record_event(user, payload.get("record_id"))
    if event.object_type == "workflowtask":
        return _can_view_workflow_task_event(user, event.object_id, payload)
    if event.object_type == "relationship":
        return _can_view_relationship_event(user, payload)
    if event.object_type == "folderchangeevent":
        return _can_view_record_event(user, payload.get("matched_record_id"))
    return False


def _can_view_record_event(user, record_id):
    record = Record.objects.filter(pk=record_id).first()
    if record is None:
        return False
    return user_can(user, "view", record.object_type_key, record_id=str(record.pk))


def _can_view_document_event(user, document_id):
    document = Document.objects.select_related("owner_record").filter(pk=document_id).first()
    if document is None:
        return False
    return user_can(
        user,
        "view",
        document.owner_record.object_type_key,
        record_id=str(document.owner_record_id),
    )


def _object_type_key_from_payload(payload):
    if not isinstance(payload, dict):
        return None
    return payload.get("object_type_key") or payload.get("target_object_type")


def _record_id_from_payload(payload):
    for key in ("record_id", "owner_record_id", "related_record_id", "matched_record_id"):
        if payload.get(key):
            return payload[key]
    return None


def _can_view_project_event(user, project_id):
    if not project_id:
        return False
    from apps.projects.models import Project

    project = Project.objects.select_related("record").filter(pk=project_id).first()
    if project is None:
        return False
    return user_can(user, "view", "project", record_id=str(project.record_id))


def _can_view_project_task_event(user, task_id):
    if not task_id:
        return False
    from apps.projects.models import ProjectTask

    task = ProjectTask.objects.select_related("project__record").filter(pk=task_id).first()
    if task is None:
        return False
    return user_can(user, "view", "project", record_id=str(task.project.record_id))


def _can_view_workflow_task_event(user, task_id, payload):
    if payload.get("related_record_id") and _can_view_record_event(user, payload["related_record_id"]):
        return True
    from apps.workflows.models import WorkflowTask

    task = WorkflowTask.objects.select_related("instance__record").filter(pk=task_id).first()
    if task is None:
        return False
    record = task.related_record or task.instance.record
    return user_can(user, "view", record.object_type_key, record_id=str(record.pk))


def _can_view_relationship_event(user, payload):
    source_id = payload.get("source_record")
    target_id = payload.get("target_record")
    return bool(
        source_id
        and target_id
        and _can_view_record_event(user, source_id)
        and _can_view_record_event(user, target_id)
    )


def _is_system_admin(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.is_superuser or user.groups.filter(name=SYSTEM_ADMIN_ROLE).exists()

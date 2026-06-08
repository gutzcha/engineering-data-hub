from django.db import transaction
from django.db.models import Max
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import records_user_can_view, user_can, user_has_view_scope
from apps.audit.services import record_audit_event
from apps.audit.views import audit_response, record_audit_events
from apps.folders.services import ManagedFolderCollisionError, generate_managed_folder
from apps.records.models import Record, RecordVersion
from apps.records.serializers import RecordSerializer, RecordVersionSerializer, _record_snapshot
from apps.records.validation import get_object_type_definition, validate_record_data
from apps.relationships.services import build_record_graph
from apps.search.tasks import enqueue_record_index


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class RecordViewSet(viewsets.ModelViewSet):
    serializer_class = RecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["object_type_key", "status"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return Record.objects.prefetch_related("documents__current_revision")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        object_type_key = self.request.query_params.get("object_type_key")
        if object_type_key and not user_has_view_scope(request.user, object_type_key):
            raise PermissionDenied("You do not have permission to view this object type.")
        queryset = records_user_can_view(request.user, queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        object_type_key = serializer.validated_data["object_type_key"]
        if not user_can(self.request.user, "create", object_type_key):
            raise PermissionDenied("You do not have permission to create this object type.")
        record = serializer.save()
        enqueue_record_index(record.pk)

    def get_object(self):
        record = super().get_object()
        if not user_can(self.request.user, "view", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to view this record.")
        return record

    def perform_update(self, serializer):
        record = self.get_object()
        if not user_can(self.request.user, "edit", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to edit this record.")
        record = serializer.save()
        enqueue_record_index(record.pk)

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        record = self.get_object()
        if not user_can(request.user, "release", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to release this record.")
        _object_type, active_config = get_object_type_definition(record.object_type_key)
        validate_record_data(record.object_type_key, record.data, current_record=record)
        before = _record_snapshot(record)
        record.status = Record.Status.RELEASED
        record.schema_version = active_config.version
        record.updated_by = request.user
        record.save(update_fields=["status", "schema_version", "updated_by", "updated_at"])
        enqueue_record_index(record.pk)
        record_audit_event(
            request.user,
            "record.released",
            record,
            before=before,
            after=_record_snapshot(record),
            request=request,
        )
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        record = self.get_object()
        if not user_can(request.user, "admin", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to archive this record.")
        before = _record_snapshot(record)
        record.status = Record.Status.ARCHIVED
        record.updated_by = request.user
        record.save(update_fields=["status", "updated_by", "updated_at"])
        enqueue_record_index(record.pk)
        record_audit_event(
            request.user,
            "record.archived",
            record,
            before=before,
            after=_record_snapshot(record),
            request=request,
        )
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"])
    def versions(self, request, pk=None):
        record = self.get_object()
        if request.method == "GET":
            if not user_can(request.user, "view", record.object_type_key, record_id=str(record.pk)):
                raise PermissionDenied("You do not have permission to view this record's versions.")
            serializer = RecordVersionSerializer(record.versions.all(), many=True)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)

        if not user_can(request.user, "edit", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to version this record.")
        with transaction.atomic():
            locked_record = Record.objects.select_for_update().get(pk=record.pk)
            next_version = (
                RecordVersion.objects.select_for_update()
                .filter(record=locked_record)
                .aggregate(max_version=Max("version_number"))["max_version"]
                or 0
            ) + 1
            version = RecordVersion.objects.create(
                record=locked_record,
                version_number=next_version,
                snapshot=_record_snapshot(locked_record),
                change_note=str(request.data.get("change_note", "")).strip(),
                created_by=request.user,
            )
            record_audit_event(
                request.user,
                "record.version_created",
                locked_record,
                before=None,
                after=RecordVersionSerializer(version).data,
                request=request,
            )
        return Response(RecordVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def graph(self, request, pk=None):
        record = self.get_object()
        return Response(build_record_graph(record, user=request.user), status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def audit(self, request, pk=None):
        record = self.get_object()
        return audit_response(record_audit_events(record))

    @action(detail=True, methods=["post"], url_path="folders/generate")
    def generate_folder(self, request, pk=None):
        record = self.get_object()
        if not user_can(request.user, "admin", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to generate folders for this record.")
        try:
            managed_folder = generate_managed_folder(record, actor=request.user, request=request)
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        except ManagedFolderCollisionError as error:
            return Response(
                {
                    "detail": "Managed folder target already exists.",
                    "relative_path": error.relative_path,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {
                "id": managed_folder.pk,
                "relative_path": managed_folder.relative_path,
                "template_key": managed_folder.template_key,
                "state": managed_folder.state,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        object_type_key = request.data.get("object_type_key")
        if object_type_key:
            get_object_type_definition(object_type_key)
            if not user_can(request.user, "create", object_type_key):
                raise PermissionDenied("You do not have permission to create this object type.")
            if request.data.get("code") and not user_can(request.user, "admin", object_type_key):
                raise PermissionDenied("Manual record codes require admin permission.")
        return super().create(request, *args, **kwargs)

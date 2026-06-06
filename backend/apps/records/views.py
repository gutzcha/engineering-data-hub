from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import user_can
from apps.records.models import Record
from apps.records.serializers import RecordSerializer
from apps.records.validation import get_object_type_definition, validate_record_data


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class RecordViewSet(viewsets.ModelViewSet):
    serializer_class = RecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["object_type_key", "status"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return Record.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        object_type_key = self.request.query_params.get("object_type_key")
        if object_type_key and not user_can(request.user, "view", object_type_key):
            raise PermissionDenied("You do not have permission to view this object type.")

        visible_keys = [
            key
            for key in queryset.values_list("object_type_key", flat=True).distinct()
            if user_can(request.user, "view", key)
        ]
        queryset = queryset.filter(object_type_key__in=visible_keys)
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
        serializer.save()

    def get_object(self):
        record = super().get_object()
        if not user_can(self.request.user, "view", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to view this record.")
        return record

    def perform_update(self, serializer):
        record = self.get_object()
        if not user_can(self.request.user, "edit", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to edit this record.")
        serializer.save()

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        record = self.get_object()
        if not user_can(request.user, "release", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to release this record.")
        _object_type, active_config = get_object_type_definition(record.object_type_key)
        validate_record_data(record.object_type_key, record.data, current_record=record)
        record.status = Record.Status.RELEASED
        record.schema_version = active_config.version
        record.updated_by = request.user
        record.save(update_fields=["status", "schema_version", "updated_by", "updated_at"])
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        object_type_key = request.data.get("object_type_key")
        if object_type_key:
            get_object_type_definition(object_type_key)
            if not user_can(request.user, "create", object_type_key):
                raise PermissionDenied("You do not have permission to create this object type.")
            if request.data.get("code") and not user_can(request.user, "admin", object_type_key):
                raise PermissionDenied("Manual record codes require admin permission.")
        return super().create(request, *args, **kwargs)

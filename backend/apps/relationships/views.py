# ===
# File Summary
# Path: backend\apps\relationships\views.py
# Type: python
# Purpose: Relationships domain for entity graph APIs and relationship operations.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: IsAuthenticated, has_permission, RelationshipViewSet, perform_create, perform_destroy
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

from rest_framework import mixins, permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.accounts.permissions import user_can
from apps.audit.services import record_audit_event
from apps.relationships.models import Relationship
from apps.relationships.serializers import RelationshipSerializer
from apps.search.tasks import enqueue_record_indexes


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class RelationshipViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Relationship.objects.select_related("source_record", "target_record")
    serializer_class = RelationshipSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "delete", "head", "options"]

    def perform_create(self, serializer):
        source_record = serializer.validated_data["source_record"]
        target_record = serializer.validated_data["target_record"]
        if not user_can(
            self.request.user,
            "edit",
            source_record.object_type_key,
            record_id=str(source_record.pk),
        ):
            raise PermissionDenied("You do not have permission to edit the source record.")
        if not user_can(
            self.request.user,
            "view",
            target_record.object_type_key,
            record_id=str(target_record.pk),
        ):
            raise PermissionDenied("You do not have permission to view the target record.")
        relationship = serializer.save()
        enqueue_record_indexes([source_record.pk, target_record.pk])
        record_audit_event(
            self.request.user,
            "relationship.created",
            relationship,
            before=None,
            after=_relationship_snapshot(relationship),
            request=self.request,
        )

    def perform_destroy(self, instance):
        if not user_can(
            self.request.user,
            "edit",
            instance.source_record.object_type_key,
            record_id=str(instance.source_record_id),
        ):
            raise PermissionDenied("You do not have permission to edit the source record.")
        before = _relationship_snapshot(instance)
        record_audit_event(
            self.request.user,
            "relationship.deleted",
            instance,
            before=before,
            after=None,
            request=self.request,
        )
        record_ids = [instance.source_record_id, instance.target_record_id]
        instance.delete()
        enqueue_record_indexes(record_ids)


def _relationship_snapshot(relationship):
    return {
        "id": relationship.pk,
        "relationship_type_key": relationship.relationship_type_key,
        "source_record": str(relationship.source_record_id),
        "target_record": str(relationship.target_record_id),
        "source_object_type_key": relationship.source_record.object_type_key,
        "target_object_type_key": relationship.target_record.object_type_key,
        "data": relationship.data.copy(),
    }


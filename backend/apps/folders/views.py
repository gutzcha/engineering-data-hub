from django.contrib.auth.models import Group
from django.db.models import QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE, user_can
from apps.accounts.models import ObjectPermission
from apps.folders.models import FolderChangeEvent
from apps.folders.serializers import FolderChangeEventSerializer


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class FolderChangeEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FolderChangeEventSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = FolderChangeEvent.objects.select_related(
            "matched_record",
            "managed_folder",
            "reviewer",
        )
        review_status = self.request.query_params.get("review_status", "pending")
        if review_status:
            queryset = queryset.filter(review_status=review_status)
        return _filter_visible_events(self.request.user, queryset)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        return self._review(request, FolderChangeEvent.ReviewStatus.ACCEPTED)

    @action(detail=True, methods=["post"])
    def ignore(self, request, pk=None):
        return self._review(request, FolderChangeEvent.ReviewStatus.IGNORED)

    @action(detail=True, methods=["post"], url_path="link-document")
    def link_document(self, request, pk=None):
        """Document linking is intentionally unavailable until Task 8."""
        self.get_object()
        return Response(
            {"detail": "Document linking is not available until documents are enabled."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    def _review(self, request, review_status):
        event = self.get_object()
        if not _can_review_event(request.user, event):
            raise PermissionDenied("You do not have permission to review this folder event.")
        event.review_status = review_status
        event.reviewer = request.user
        event.save(update_fields=["review_status", "reviewer", "updated_at"])
        return Response(self.get_serializer(event).data)


def _can_review_event(user, event):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    if _is_system_admin(user):
        return True
    if not event.matched_record:
        return False
    return user_can(
        user,
        "edit",
        event.matched_record.object_type_key,
        record_id=str(event.matched_record_id),
    )


def _filter_visible_events(user, queryset):
    if not user or not user.is_authenticated or not user.is_active:
        return queryset.none() if isinstance(queryset, QuerySet) else FolderChangeEvent.objects.none()
    if user.is_superuser or _is_system_admin(user):
        return queryset

    role_names = user.groups.values_list("name", flat=True)
    visible_object_type_keys = ObjectPermission.objects.filter(
        role_name__in=role_names,
        can_view=True,
    ).values_list("object_type_key", flat=True)
    return queryset.filter(matched_record__object_type_key__in=visible_object_type_keys)


def _is_system_admin(user):
    return Group.objects.filter(user=user, name=SYSTEM_ADMIN_ROLE).exists()

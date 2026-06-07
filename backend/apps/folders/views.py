from pathlib import Path, PurePosixPath

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q, QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE, records_user_can_view, user_can
from apps.audit.services import record_audit_event, snapshot_model
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer
from apps.folders.models import FolderChangeEvent
from apps.folders.serializers import FolderChangeEventSerializer
from apps.folders.services import validate_relative_path
from apps.search.tasks import enqueue_folder_event_index


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
            "managed_folder__record",
            "reviewer",
            "assigned_to",
        )
        default_review_status = "pending" if getattr(self, "action", None) == "list" else ""
        review_status = self.request.query_params.get("review_status", default_review_status)
        if review_status:
            queryset = queryset.filter(review_status=review_status)
        record_id = self.request.query_params.get("record") or self.request.query_params.get(
            "matched_record"
        )
        if record_id:
            queryset = queryset.filter(
                Q(matched_record_id=record_id) | Q(managed_folder__record_id=record_id)
            )
        return _filter_visible_events(self.request.user, queryset)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        return self._review(request, FolderChangeEvent.ReviewStatus.ACCEPTED)

    @action(detail=True, methods=["post"])
    def ignore(self, request, pk=None):
        return self._review(request, FolderChangeEvent.ReviewStatus.IGNORED)

    @action(detail=True, methods=["post"], url_path="link-document")
    def link_document(self, request, pk=None):
        event = self.get_object()
        if not _can_review_event(request.user, event):
            raise PermissionDenied("You do not have permission to review this folder event.")

        record = _event_record(event)
        if record is None:
            raise ValidationError({"matched_record": ["Folder event must be matched to a record."]})
        before = _folder_event_snapshot(event)
        linked_path = _safe_linked_path(event)
        title = (request.data.get("title") or PurePosixPath(linked_path).name or event.path).strip()
        document_type = (request.data.get("document_type") or "folder_event").strip()

        with transaction.atomic():
            document = Document.objects.create(
                title=title,
                owner_record=record,
                document_type=document_type,
                folder=event.managed_folder,
            )
            event.review_status = FolderChangeEvent.ReviewStatus.LINKED
            event.reviewer = request.user
            event.save(update_fields=["review_status", "reviewer", "updated_at"])
            enqueue_folder_event_index(event.pk)
            after = _folder_event_snapshot(event)
            after["linked_document_id"] = document.pk
            after["linked_path"] = linked_path
            record_audit_event(
                request.user,
                "folder_event.document_linked",
                event,
                before=before,
                after=after,
                request=request,
            )

        return Response(
            {
                "event": self.get_serializer(event).data,
                "document": DocumentSerializer(document).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        event = self.get_object()
        if not _can_review_event(request.user, event):
            raise PermissionDenied("You do not have permission to review this folder event.")
        before = _folder_event_snapshot(event)
        event.assigned_to = _assignee_from_request(request)
        event.save(update_fields=["assigned_to", "updated_at"])
        enqueue_folder_event_index(event.pk)
        record_audit_event(
            request.user,
            "folder_event.assigned",
            event,
            before=before,
            after=_folder_event_snapshot(event),
            request=request,
        )
        return Response(self.get_serializer(event).data)

    def _review(self, request, review_status):
        event = self.get_object()
        if not _can_review_event(request.user, event):
            raise PermissionDenied("You do not have permission to review this folder event.")
        before = _folder_event_snapshot(event)
        event.review_status = review_status
        event.reviewer = request.user
        event.save(update_fields=["review_status", "reviewer", "updated_at"])
        enqueue_folder_event_index(event.pk)
        record_audit_event(
            request.user,
            f"folder_event.{review_status}",
            event,
            before=before,
            after=_folder_event_snapshot(event),
            request=request,
        )
        return Response(self.get_serializer(event).data)


def _can_review_event(user, event):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    if _is_system_admin(user):
        return True
    record = _event_record(event)
    if not record:
        return False
    return user_can(
        user,
        "edit",
        record.object_type_key,
        record_id=str(record.pk),
    )


def _filter_visible_events(user, queryset):
    if not user or not user.is_authenticated or not user.is_active:
        return queryset.none() if isinstance(queryset, QuerySet) else FolderChangeEvent.objects.none()
    if user.is_superuser or _is_system_admin(user):
        return queryset

    from apps.records.models import Record

    visible_record_ids = records_user_can_view(
        user,
        Record.objects.filter(
            Q(folder_change_events__isnull=False) | Q(managed_folders__change_events__isnull=False)
        ),
    ).values_list("pk", flat=True).distinct()
    return queryset.filter(
        Q(matched_record_id__in=visible_record_ids)
        | Q(managed_folder__record_id__in=visible_record_ids)
    )


def _is_system_admin(user):
    return Group.objects.filter(user=user, name=SYSTEM_ADMIN_ROLE).exists()


def _folder_event_snapshot(event):
    return snapshot_model(
        event,
        [
            "id",
            "event_type",
            "path",
            "detected_hash",
            "matched_record_id",
            "managed_folder_id",
            "review_status",
            "reviewer_id",
            "assigned_to_id",
        ],
    )


def _assignee_from_request(request):
    assignee_id = request.data.get("assignee", request.data.get("assigned_to", None))
    if assignee_id in (None, ""):
        return None
    user = get_user_model().objects.filter(pk=assignee_id, is_active=True).first()
    if user is None:
        raise ValidationError({"assigned_to": ["Assignee must be an active user."]})
    return user


def _event_record(event):
    if event.matched_record:
        return event.matched_record
    if event.managed_folder:
        return event.managed_folder.record
    return None


def _safe_linked_path(event):
    if event.managed_folder is None:
        raise ValidationError({"managed_folder": ["Folder event must belong to a managed folder."]})

    event_path = event.path.split("->")[-1].strip()
    relative_event_path = validate_relative_path(event_path)
    folder_relative_path = validate_relative_path(event.managed_folder.relative_path)

    try:
        relative_to_folder = PurePosixPath(relative_event_path).relative_to(
            PurePosixPath(folder_relative_path)
        )
    except ValueError as error:
        raise ValidationError({"path": ["Folder event path must be inside the managed folder."]}) from error

    relative_to_folder = validate_relative_path(relative_to_folder.as_posix())
    folder_root = Path(event.managed_folder.absolute_path).resolve(strict=False)
    candidate = folder_root.joinpath(*PurePosixPath(relative_to_folder).parts).resolve(strict=False)
    if candidate != folder_root and folder_root not in candidate.parents:
        raise ValidationError({"path": ["Folder event path must stay inside the managed folder."]})
    return relative_event_path

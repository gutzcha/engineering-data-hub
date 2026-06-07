from django.db import IntegrityError, transaction
from django.http import Http404
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import user_can
from apps.audit.services import record_audit_event, snapshot_model
from apps.audit.views import audit_response, document_audit_events
from apps.documents.extraction import extract_text
from apps.documents.models import Document, DocumentEvent, DocumentRevision
from apps.documents.serializers import DocumentRevisionSerializer, DocumentSerializer
from apps.documents.storage import (
    delete_storage_path,
    discard_finalized_revision_file,
    discard_uploaded_revision_file,
    finalize_uploaded_revision_file,
    path_for_storage_path,
    save_uploaded_revision_file,
)
from apps.folders.models import ManagedFolder
from apps.records.models import Record


PREVIEW_TEXT_CHARS = 20_000


class RevisionConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Revision conflict."
    default_code = "revision_conflict"


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class DocumentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request):
        owner_record = get_object_or_404(Record, pk=request.data.get("owner_record"))
        self._require_record_permission(request.user, "edit", owner_record)
        folder = self._get_folder(request.data.get("folder"), owner_record)
        serializer = DocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = request.FILES.get("file")
        revision_label = (request.data.get("revision_label") or "").strip()
        if bool(uploaded_file) != bool(revision_label):
            return Response(
                {"revision_label": ["Revision label and file are required together."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            document = Document.objects.create(
                title=serializer.validated_data["title"],
                owner_record=owner_record,
                document_type=serializer.validated_data["document_type"],
                folder=folder,
            )
            _record_event(document, None, "document_created", request.user)
            if uploaded_file:
                revision = _create_or_replace_revision(
                    document=document,
                    revision_label=revision_label,
                    uploaded_file=uploaded_file,
                    actor=request.user,
                )
                document.current_revision = revision
                document.save(update_fields=["current_revision", "updated_at"])
            record_audit_event(
                request.user,
                "document.created",
                document,
                before=None,
                after=_document_snapshot(document),
                request=request,
            )

        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def revisions(self, request, pk=None):
        document = self._get_document(pk)
        self._require_record_permission(request.user, "edit", document.owner_record)
        revision_label = (request.data.get("revision_label") or "").strip()
        uploaded_file = request.FILES.get("file")
        if not revision_label:
            return Response(
                {"revision_label": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if uploaded_file is None:
            return Response({"file": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            document = self._lock_document(document.pk)
            before = _document_snapshot(document)
            revision = _create_or_replace_revision(
                document=document,
                revision_label=revision_label,
                uploaded_file=uploaded_file,
                actor=request.user,
            )
            if document.state == Document.State.DRAFT:
                document.current_revision = revision
                document.save(update_fields=["current_revision", "updated_at"])
            record_audit_event(
                request.user,
                "document.revision_saved",
                document,
                before=before,
                after=_document_snapshot(document),
                request=request,
            )

        return Response(DocumentRevisionSerializer(revision).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path=r"revisions/(?P<revision_id>[^/.]+)/release")
    def release_revision(self, request, pk=None, revision_id=None):
        document = self._get_document(pk)
        self._require_record_permission(request.user, "release", document.owner_record)

        with transaction.atomic():
            document = self._lock_document(document.pk)
            before = _document_snapshot(document)
            revision = get_object_or_404(
                DocumentRevision.objects.select_for_update(),
                pk=revision_id,
                document=document,
            )
            if revision.state != DocumentRevision.State.RELEASED:
                revision.state = DocumentRevision.State.RELEASED
                revision.released_at = timezone.now()
                revision.save(update_fields=["state", "released_at", "updated_at"])
                _record_event(document, revision, "revision_released", request.user)
            document.current_revision = revision
            document.state = Document.State.RELEASED
            document.save(update_fields=["current_revision", "state", "updated_at"])
            record_audit_event(
                request.user,
                "document.revision_released",
                document,
                before=before,
                after=_document_snapshot(document),
                request=request,
            )

        return Response(DocumentRevisionSerializer(revision).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        document = self._get_document(pk)
        self._require_record_permission(request.user, "view", document.owner_record)
        revision = self._current_revision_or_404(document)
        path = path_for_storage_path(revision.storage_path)
        if not path.exists():
            return _missing_storage_response(document, revision, request.user)
        try:
            file_handle = path.open("rb")
        except FileNotFoundError:
            return _missing_storage_response(document, revision, request.user)
        response = FileResponse(
            file_handle,
            content_type=revision.mime_type or "application/octet-stream",
            as_attachment=True,
            filename=revision.file_name,
        )
        return response

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        document = self._get_document(pk)
        self._require_record_permission(request.user, "view", document.owner_record)
        revision = self._current_revision_or_404(document)
        extracted_text = revision.extracted_text[:PREVIEW_TEXT_CHARS]
        return Response(
            {
                "document": document.pk,
                "revision": revision.pk,
                "revision_label": revision.revision_label,
                "file_name": revision.file_name,
                "mime_type": revision.mime_type,
                "extraction_status": revision.extraction_status,
                "extracted_text": extracted_text,
                "truncated": len(revision.extracted_text) > PREVIEW_TEXT_CHARS,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def audit(self, request, pk=None):
        document = self._get_document(pk)
        self._require_record_permission(request.user, "view", document.owner_record)
        return audit_response(document_audit_events(document))

    def _get_document(self, pk):
        return get_object_or_404(
            Document.objects.select_related("owner_record", "current_revision", "folder"),
            pk=pk,
        )

    def _lock_document(self, pk):
        return get_object_or_404(
            Document.objects.select_for_update().select_related(
                "owner_record",
                "current_revision",
                "folder",
            ),
            pk=pk,
        )

    def _get_folder(self, folder_id, owner_record):
        if not folder_id:
            return None
        folder = get_object_or_404(ManagedFolder, pk=folder_id)
        if folder.record_id != owner_record.pk:
            raise PermissionDenied("Folder must belong to the owner record.")
        return folder

    def _current_revision_or_404(self, document):
        if not document.current_revision:
            raise Http404("Document has no current revision.")
        return document.current_revision

    def _require_record_permission(self, user, action, record):
        if not user_can(user, action, record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied(f"You do not have permission to {action} this document.")


def _create_or_replace_revision(document, revision_label: str, uploaded_file, actor):
    revision = DocumentRevision.objects.select_for_update().filter(
        document=document,
        revision_label=revision_label,
    ).first()
    if revision and revision.state == DocumentRevision.State.RELEASED:
        raise _revision_label_error("Released revisions cannot be replaced. Use a new revision label.")

    action = "revision_replaced" if revision else "revision_created"
    if revision is None:
        try:
            revision = DocumentRevision.objects.create(
                document=document,
                revision_label=revision_label,
                file_name="",
                storage_path="",
                sha256="",
                created_by=actor,
            )
        except IntegrityError as error:
            raise RevisionConflict({"revision_label": ["Revision label already exists."]}) from error

    before = _revision_snapshot(revision)
    previous_storage_path = revision.storage_path
    file_data = save_uploaded_revision_file(document.pk, revision.pk, uploaded_file)
    try:
        revision.refresh_from_db()
        if revision.state == DocumentRevision.State.RELEASED:
            raise _revision_label_error(
                "Released revisions cannot be replaced. Use a new revision label."
            )
        extracted_text, extraction_status = extract_text(
            file_data["absolute_path"],
            file_data["mime_type"],
            file_data["file_name"],
        )
        revision.refresh_from_db()
        if revision.state == DocumentRevision.State.RELEASED:
            raise _revision_label_error(
                "Released revisions cannot be replaced. Use a new revision label."
            )
        finalize_uploaded_revision_file(file_data)
    except Exception:
        discard_uploaded_revision_file(file_data)
        raise

    revision.file_name = file_data["file_name"]
    revision.storage_path = file_data["storage_path"]
    revision.sha256 = file_data["sha256"]
    revision.size = file_data["size"]
    revision.mime_type = file_data["mime_type"]
    revision.extracted_text = extracted_text
    revision.extraction_status = extraction_status
    revision.created_by = actor
    try:
        revision.save(
            update_fields=[
                "file_name",
                "storage_path",
                "sha256",
                "size",
                "mime_type",
                "extracted_text",
                "extraction_status",
                "created_by",
                "updated_at",
            ]
        )
        _record_event(
            document,
            revision,
            action,
            actor,
            {"before": before, "after": _revision_snapshot(revision)},
        )
    except Exception:
        discard_finalized_revision_file(file_data)
        raise
    if previous_storage_path and previous_storage_path != revision.storage_path:
        transaction.on_commit(lambda: delete_storage_path(previous_storage_path))
    return revision


def _record_event(document, revision, action: str, actor, data=None):
    return DocumentEvent.objects.create(
        document=document,
        revision=revision,
        action=action,
        actor=actor,
        data=data or {},
    )


def _document_snapshot(document):
    return snapshot_model(
        document,
        [
            "id",
            "title",
            "owner_record_id",
            "document_type",
            "current_revision_id",
            "state",
            "folder_id",
        ],
    )


def _missing_storage_response(document, revision, actor):
    _record_event(document, revision, "storage_missing", actor)
    return Response(
        {"detail": "Document file is missing from storage."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _revision_label_error(message):
    from rest_framework import serializers

    raise serializers.ValidationError({"revision_label": [message]})


def _revision_snapshot(revision):
    return {
        "file_name": revision.file_name,
        "sha256": revision.sha256,
        "size": revision.size,
        "storage_path": revision.storage_path,
        "state": revision.state,
    }

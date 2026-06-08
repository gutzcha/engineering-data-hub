from django.core.exceptions import ValidationError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE, user_can
from apps.search.client import get_search_client
from apps.search.indexers import DOCUMENTS_INDEX, FOLDER_EVENTS_INDEX, PROJECTS_INDEX, RECORDS_INDEX


SEARCHABLE_INDEXES = {
    "records": RECORDS_INDEX,
    "documents": DOCUMENTS_INDEX,
    "folder_events": FOLDER_EVENTS_INDEX,
    "projects": PROJECTS_INDEX,
}
ALL_INDEXES = tuple(SEARCHABLE_INDEXES.values())


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response({"results": []}, status=status.HTTP_200_OK)

        requested_type = request.query_params.get("type", "all")
        indexes = _indexes_for_type(requested_type)
        if indexes is None:
            return Response(
                {"type": ["Unsupported search type."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client = get_search_client()
        if not client.enabled:
            return Response({"results": []}, status=status.HTTP_200_OK)

        results = []
        for index_name in indexes:
            response = client.search(
                index_name,
                query,
                attributesToHighlight=["*"],
                highlightPreTag="<em>",
                highlightPostTag="</em>",
                limit=20,
            )
            for hit in _hits_from_response(response):
                authorized_hit = _authorized_hit(request.user, index_name, hit)
                if authorized_hit:
                    results.append(map_search_hit(index_name, authorized_hit))
        return Response({"results": results}, status=status.HTTP_200_OK)


def map_search_hit(index_name, hit):
    formatted = hit.get("_formatted") or {}
    if index_name == RECORDS_INDEX:
        return {
            "type": "record",
            "title": hit.get("title", ""),
            "code": hit.get("code", ""),
            "snippet": _snippet(formatted, hit, ["data_text", "relationship_text", "title"]),
            "object_type_key": hit.get("object_type_key", ""),
            "status": hit.get("status", ""),
            "url": f"/records/{hit.get('id', '')}",
        }
    if index_name == DOCUMENTS_INDEX:
        document_id = hit.get("document_id") or hit.get("id", "")
        return {
            "type": "document",
            "title": hit.get("title", ""),
            "code": hit.get("filename") or hit.get("revision", ""),
            "snippet": _snippet(formatted, hit, ["extracted_text", "title", "filename"]),
            "object_type_key": hit.get("object_type_key", ""),
            "status": hit.get("state", ""),
            "url": f"/documents/{document_id}",
        }
    if index_name == FOLDER_EVENTS_INDEX:
        return {
            "type": "folder_event",
            "title": hit.get("path", ""),
            "code": hit.get("record_code", ""),
            "snippet": _snippet(formatted, hit, ["path", "record_title", "event_type"]),
            "object_type_key": hit.get("object_type_key", ""),
            "status": hit.get("review_status", ""),
            "url": f"/folder-events/{hit.get('id', '')}",
        }
    return {
        "type": "project",
        "title": hit.get("title", ""),
        "code": hit.get("code", ""),
        "snippet": _snippet(formatted, hit, ["description", "title"]),
        "object_type_key": hit.get("object_type_key", ""),
        "status": hit.get("status", ""),
        "url": f"/projects/{hit.get('id', '')}",
    }


def _indexes_for_type(requested_type):
    if requested_type == "all":
        return ALL_INDEXES
    index_name = SEARCHABLE_INDEXES.get(requested_type)
    if not index_name:
        return None
    return (index_name,)


def _snippet(formatted, hit, fields):
    for field in fields:
        value = formatted.get(field) or hit.get(field)
        if value:
            return value
    return ""


def _user_can_view_hit(user, index_name, hit):
    return _authorized_hit(user, index_name, hit) is not None


def _authorized_hit(user, index_name, hit):
    if _is_search_admin(user):
        return hit
    if index_name == RECORDS_INDEX:
        return _authorized_record_hit(user, hit)
    if index_name == DOCUMENTS_INDEX:
        return _authorized_document_hit(user, hit)
    if index_name == FOLDER_EVENTS_INDEX:
        return _authorized_folder_event_hit(user, hit)
    if index_name == PROJECTS_INDEX:
        return _authorized_project_hit(user, hit)
    return None


def _hits_from_response(response):
    if not isinstance(response, dict) or not isinstance(response.get("hits"), list):
        return []
    return [hit for hit in response["hits"] if isinstance(hit, dict)]


def _is_search_admin(user):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=SYSTEM_ADMIN_ROLE).exists()


def _authorized_record_hit(user, hit):
    from apps.records.models import Record

    record_id = hit.get("id")
    if not record_id:
        return None
    try:
        record = Record.objects.filter(pk=record_id).first()
    except (ValueError, ValidationError):
        return None
    if not record:
        return None
    if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
        return None
    return {
        **hit,
        "id": str(record.pk),
        "object_type_key": record.object_type_key,
        "code": record.code,
        "title": record.title,
        "status": record.status,
    }


def _authorized_document_hit(user, hit):
    revision = _document_revision_for_hit(hit)
    if not revision:
        return None
    record = revision.document.owner_record
    if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
        return None
    return {
        **hit,
        "id": str(revision.pk),
        "document_id": str(revision.document_id),
        "record_id": str(record.pk),
        "title": revision.document.title,
        "revision": revision.revision_label,
        "state": revision.state,
        "filename": revision.file_name,
        "object_type_key": record.object_type_key,
    }


def _authorized_folder_event_hit(user, hit):
    from apps.folders.models import FolderChangeEvent

    event_id = hit.get("id")
    if not event_id:
        return None
    try:
        event = (
            FolderChangeEvent.objects.select_related("matched_record", "managed_folder__record")
            .filter(pk=event_id)
            .first()
        )
    except (ValueError, ValidationError):
        return None
    if not event:
        return None
    record = _folder_event_record(event)
    if not record:
        return None
    if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
        return None
    return {
        **hit,
        "id": str(event.pk),
        "event_type": event.event_type,
        "path": event.path,
        "review_status": event.review_status,
        "record_id": str(record.pk),
        "record_code": record.code,
        "record_title": record.title,
        "object_type_key": record.object_type_key,
    }


def _authorized_project_hit(user, hit):
    from apps.projects.models import Project

    project_id = hit.get("id")
    if not project_id:
        return None
    try:
        project = Project.objects.select_related("record").filter(pk=project_id).first()
    except (ValueError, ValidationError):
        return None
    if not project:
        return None
    record = project.record
    if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
        return None
    return {
        **hit,
        "id": str(project.pk),
        "record_id": str(record.pk),
        "object_type_key": record.object_type_key,
        "code": record.code,
        "title": project.name,
        "status": project.status,
        "description": project.description,
    }


def _folder_event_record(event):
    if event.matched_record:
        return event.matched_record
    if event.managed_folder:
        return event.managed_folder.record
    return None


def _document_revision_for_hit(hit):
    from apps.documents.models import DocumentRevision

    revision_id = hit.get("id")
    if not revision_id:
        return None
    try:
        revision = (
            DocumentRevision.objects.select_related("document__owner_record")
            .filter(pk=revision_id)
            .first()
        )
    except (ValueError, ValidationError):
        return None
    if not revision:
        return None
    return revision

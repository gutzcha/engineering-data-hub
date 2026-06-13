# ===
# File Summary
# Path: backend\apps\search\views.py
# Type: python
# Purpose: Search domain for indexing payload generation and search query APIs.
# Primary responsibilities:
# - Core symbols: SearchView, get, map_search_hit
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===

from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE, records_user_can_view, user_can
from apps.search.client import get_search_client
from apps.search.indexers import DOCUMENTS_INDEX, FOLDER_EVENTS_INDEX, PROJECTS_INDEX, RECORDS_INDEX


SEARCH_INDEX_ORDER = [RECORDS_INDEX, DOCUMENTS_INDEX, PROJECTS_INDEX, FOLDER_EVENTS_INDEX]
ALL_INDEXES = tuple(SEARCH_INDEX_ORDER)


SECTION_LABELS = {
    RECORDS_INDEX: ("records", "Records"),
    DOCUMENTS_INDEX: ("documents", "Documents"),
    PROJECTS_INDEX: ("projects", "Projects"),
    FOLDER_EVENTS_INDEX: ("folder_events", "Folder Review Events"),
}


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        requested_type = request.query_params.get("type", "all")
        object_type_filter = (request.query_params.get("object_type_key") or "").strip()
        status_filter = (request.query_params.get("status") or "").strip()

        tags_filter = _parse_filter_values(request.query_params, "tags")
        application_filter = _parse_filter_values(request.query_params, "application")
        resin_family_filter = _parse_filter_values(request.query_params, "resin_family")
        color_filter = _parse_filter_values(request.query_params, "color")
        project_status_filter = _normalize_filter_values(_parse_filter_values(request.query_params, "project_status"))
        form_fields_filter = _normalize_field_list(_parse_filter_values(request.query_params, "form_fields"))

        search_filters = {
            "tags": _normalize_filter_values(tags_filter),
            "application": _normalize_filter_values(application_filter),
            "resin_family": _normalize_filter_values(resin_family_filter),
            "color": _normalize_filter_values(color_filter),
            "project_status": project_status_filter,
            "form_fields": form_fields_filter,
        }

        status_values = _normalized_status_values(status_filter)
        include_sections = bool(
            object_type_filter
            or status_values
            or requested_type != "all"
            or _has_active_search_filters(search_filters)
        )
        if not query and not include_sections:
            return Response({"results": []}, status=status.HTTP_200_OK)

        indexes = _indexes_for_type(requested_type)
        if indexes is None:
            return Response(
                {"type": ["Unsupported search type."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client = get_search_client()
        if client.enabled:
            results_by_index = _search_in_meili(
                client=client,
                query=query,
                user=request.user,
                indexes=indexes,
                object_type_filter=object_type_filter,
                status_values=status_values,
                search_filters=search_filters,
            )
        else:
            results_by_index = _search_in_database(
                query=query,
                user=request.user,
                requested_type=requested_type,
                object_type_filter=object_type_filter,
                status_values=status_values,
                search_filters=search_filters,
            )

        flat_results = [hit for index_name in SEARCH_INDEX_ORDER for hit in results_by_index.get(index_name, [])]

        if not include_sections:
            return Response({"results": flat_results}, status=status.HTTP_200_OK)

        sections = _build_sections(results_by_index)
        return Response(
            {
                "results": flat_results,
                "sections": sections,
                "count": sum(section["count"] for section in sections),
            },
            status=status.HTTP_200_OK,
        )


def map_search_hit(index_name, hit):
    formatted = hit.get("_formatted") or {}
    if index_name == RECORDS_INDEX:
        return {
            "type": "record",
            "record_id": str(hit.get("id", "")),
            "title": hit.get("title", ""),
            "code": hit.get("code", ""),
            "snippet": _snippet(formatted, hit, ["data_text", "relationship_text", "title"]),
            "object_type_key": hit.get("object_type_key", ""),
            "status": hit.get("status", ""),
            "url": f"/records/{hit.get('id', '')}",
        }
    if index_name == DOCUMENTS_INDEX:
        return {
            "type": "document",
            "record_id": hit.get("record_id"),
            "title": hit.get("title", ""),
            "code": hit.get("filename") or hit.get("revision", ""),
            "snippet": _snippet(formatted, hit, ["extracted_text", "title", "filename"]),
            "object_type_key": hit.get("object_type_key", ""),
            "status": hit.get("state", ""),
            "url": f"/documents/{hit.get('document_id') or ''}",
        }
    if index_name == FOLDER_EVENTS_INDEX:
        return {
            "type": "folder_event",
            "record_id": hit.get("record_id"),
            "title": hit.get("path", ""),
            "code": hit.get("record_code", ""),
            "snippet": _snippet(formatted, hit, ["path", "record_title", "event_type"]),
            "object_type_key": hit.get("object_type_key", ""),
            "status": hit.get("review_status", ""),
            "url": f"/tasks/folder-events/{hit.get('id', '')}",
        }
    return {
        "type": "project",
        "record_id": hit.get("record_id"),
        "project_id": hit.get("project_id"),
        "id": str(hit.get("id", "")),
        "title": hit.get("title", ""),
        "code": hit.get("code", ""),
        "snippet": hit.get("description") or hit.get("name"),
        "object_type_key": "project",
        "status": hit.get("status", ""),
        "url": f"/projects/{hit.get('id', '')}",
    }


def _indexes_for_type(requested_type):
    if requested_type == "all":
        return ALL_INDEXES
    index_name = _index_name_for_type(requested_type)
    if index_name is None:
        return None
    return (index_name,)


def _index_name_for_type(requested_type):
    if requested_type == "records":
        return RECORDS_INDEX
    if requested_type == "documents":
        return DOCUMENTS_INDEX
    if requested_type == "projects":
        return PROJECTS_INDEX
    if requested_type == "folder_events":
        return FOLDER_EVENTS_INDEX
    return None


def _snippet(formatted, hit, fields):
    for field in fields:
        value = formatted.get(field) or hit.get(field)
        if value:
            return value
    return ""


def _search_in_meili(client, query, user, indexes, object_type_filter, status_values, search_filters):
    results_by_index = {}
    for index_name in indexes:
        response = client.search(
            index_name,
            query,
            attributesToHighlight=["*"],
            highlightPreTag="<em>",
            highlightPostTag="</em>",
            limit=50,
        )
        section = []
        for hit in _hits_from_response(response):
            authorized_hit = _authorized_hit(user, index_name, hit)
            if not authorized_hit:
                continue
            result = map_search_hit(index_name, authorized_hit)
            if _search_result_matches_filters(
                result,
                object_type_filter=object_type_filter,
                status_values=status_values,
                search_filters=search_filters,
                user=user,
            ):
                section.append(result)
        results_by_index[index_name] = section[:20]
    return results_by_index


def _search_in_database(
    query,
    user,
    requested_type,
    object_type_filter,
    status_values,
    search_filters,
):
    indexes = _indexes_for_type(requested_type)
    results_by_index = {index_name: [] for index_name in indexes}
    if RECORDS_INDEX in results_by_index:
        results_by_index[RECORDS_INDEX] = _search_records_in_database(
            query=query,
            user=user,
            object_type_filter=object_type_filter,
            status_values=status_values,
            search_filters=search_filters,
        )
    if DOCUMENTS_INDEX in results_by_index:
        results_by_index[DOCUMENTS_INDEX] = _search_documents_in_database(
            query=query,
            user=user,
            object_type_filter=object_type_filter,
            status_values=status_values,
            search_filters=search_filters,
        )
    if PROJECTS_INDEX in results_by_index:
        results_by_index[PROJECTS_INDEX] = _search_projects_in_database(
            query=query,
            user=user,
            object_type_filter=object_type_filter,
            status_values=status_values,
            search_filters=search_filters,
        )
    if FOLDER_EVENTS_INDEX in results_by_index:
        results_by_index[FOLDER_EVENTS_INDEX] = _search_folder_events_in_database(
            query=query,
            user=user,
            object_type_filter=object_type_filter,
            status_values=status_values,
            search_filters=search_filters,
        )
    return results_by_index


def _search_records_in_database(query, user, object_type_filter, status_values, search_filters):
    from apps.records.models import Record

    queryset = Record.objects.all()
    if query:
        queryset = queryset.filter(
            Q(code__icontains=query) | Q(title__icontains=query) | Q(data__icontains=query)
        )
    if object_type_filter:
        queryset = queryset.filter(object_type_key__iexact=object_type_filter)
    if status_values:
        queryset = queryset.filter(status__in=list(status_values))
    if object_type_filter and object_type_filter.lower() == "project" and search_filters["project_status"]:
        queryset = queryset.filter(status__in=search_filters["project_status"])
    queryset = records_user_can_view(user, queryset)
    if not _search_filters_require_record_data(search_filters):
        return [_serialize_record_hit(record) for record in queryset[:20]]

    results = []
    for record in queryset:
        if _record_matches_filters(record, search_filters):
            results.append(_serialize_record_hit(record))
            if len(results) >= 20:
                break
    return results


def _search_documents_in_database(query, user, object_type_filter, status_values, search_filters):
    from apps.documents.models import DocumentRevision

    queryset = DocumentRevision.objects.select_related("document__owner_record").all()
    if query:
        queryset = queryset.filter(
            Q(file_name__icontains=query)
            | Q(document__title__icontains=query)
            | Q(document__owner_record__code__icontains=query)
            | Q(document__owner_record__title__icontains=query)
            | Q(extracted_text__icontains=query)
        )
    if status_values:
        queryset = queryset.filter(state__in=list(status_values))
    if object_type_filter:
        queryset = queryset.filter(document__owner_record__object_type_key__iexact=object_type_filter)

    results = []
    for revision in queryset:
        record = revision.document.owner_record
        if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
            continue
        if _search_filters_require_record_data(search_filters) and not _record_matches_filters(record, search_filters):
            continue
        result = map_search_hit(
            DOCUMENTS_INDEX,
            {
                "id": str(revision.pk),
                "document_id": str(revision.document_id),
                "record_id": str(record.pk),
                "title": revision.document.title,
                "revision": revision.revision_label,
                "state": revision.state,
                "filename": revision.file_name,
                "object_type_key": record.object_type_key,
            },
        )
        results.append(result)
        if len(results) >= 20:
            break
    return results


def _search_projects_in_database(query, user, object_type_filter, status_values, search_filters):
    from apps.projects.models import Project
    from apps.records.models import Record

    if object_type_filter and object_type_filter.lower() != "project":
        return []

    visible_record_ids = records_user_can_view(
        user,
        Record.objects.filter(object_type_key="project"),
    ).values_list("pk", flat=True)
    queryset = Project.objects.select_related("record").filter(record_id__in=list(visible_record_ids))

    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(record__code__icontains=query)
            | Q(record__title__icontains=query)
        )

    if search_filters["project_status"]:
        queryset = queryset.filter(status__in=search_filters["project_status"])

    if status_values:
        # Ensure "status" also remains aligned with primary search status filter when present.
        if search_filters["project_status"]:
            queryset = queryset.filter(status__in=[value for value in status_values if value in search_filters["project_status"]])
        else:
            queryset = queryset.filter(status__in=list(status_values))

    if not _search_filters_require_record_data(search_filters):
        return [_serialize_project_hit(project) for project in queryset[:20]]

    results = []
    for project in queryset:
        if _record_matches_filters(project.record, search_filters):
            results.append(_serialize_project_hit(project))
            if len(results) >= 20:
                break
    return results


def _search_folder_events_in_database(query, user, object_type_filter, status_values, search_filters):
    from apps.folders.models import FolderChangeEvent

    queryset = FolderChangeEvent.objects.select_related("matched_record", "managed_folder__record").all()
    if query:
        queryset = queryset.filter(Q(path__icontains=query) | Q(event_type__icontains=query))
    if status_values:
        queryset = queryset.filter(review_status__in=list(status_values))

    results = []
    for event in queryset:
        record = event.matched_record or (event.managed_folder.record if event.managed_folder else None)
        if not record:
            if object_type_filter:
                continue
            if _search_filters_require_record_data(search_filters):
                continue
            # If user is not elevated, skip orphaned items to avoid leaking unscoped data.
            if not _is_search_admin(user):
                continue
            results.append(
                map_search_hit(
                    FOLDER_EVENTS_INDEX,
                    {
                        "id": str(event.pk),
                        "event_type": event.event_type,
                        "path": event.path,
                        "record_id": "",
                        "record_code": "",
                        "record_title": "",
                        "object_type_key": "",
                        "review_status": event.review_status,
                    },
                )
            )
            continue

        if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
            continue
        if object_type_filter and record.object_type_key.lower() != object_type_filter.lower():
            continue
        if _search_filters_require_record_data(search_filters) and not _record_matches_filters(record, search_filters):
            continue

        results.append(
            map_search_hit(
                FOLDER_EVENTS_INDEX,
                {
                    "id": str(event.pk),
                    "event_type": event.event_type,
                    "path": event.path,
                    "record_id": str(record.pk),
                    "record_code": record.code,
                    "record_title": record.title,
                    "object_type_key": record.object_type_key,
                    "review_status": event.review_status,
                },
            )
        )
        if len(results) >= 20:
            break
    return results


def _serialize_record_hit(record):
    return {
        "type": "record",
        "title": record.title,
        "code": record.code,
        "snippet": record.title,
        "object_type_key": record.object_type_key,
        "status": record.status,
        "record_id": str(record.pk),
        "url": f"/records/{record.pk}",
    }


def _serialize_project_hit(project):
    project_id = str(project.pk)
    return {
        "type": "project",
        "title": project.name,
        "id": project_id,
        "code": project.record.code if project.record else "",
        "snippet": project.description or project.name,
        "object_type_key": "project",
        "status": project.status,
        "record_id": str(project.record_id),
        "project_id": project_id,
        "url": f"/projects/{project.pk}",
    }


def _build_sections(results_by_index):
    return [
        {"key": section_key, "label": label, "count": len(items), "items": items}
        for index_name in SEARCH_INDEX_ORDER
        if index_name in results_by_index
        for section_key, label in [SECTION_LABELS[index_name]]
        if (items := [item for item in results_by_index.get(index_name, []) if item])
    ]


def _normalized_status_values(raw_status):
    if not raw_status:
        return None

    raw_values = [value.strip().lower() for value in raw_status.split(",") if value.strip()]
    if not raw_values:
        return None

    aliases = {
        "active": {"active", "draft", "planning", "open", "todo", "in_progress"},
        "review": {"review", "pending", "qa_review"},
        "ready": {"ready", "released", "complete", "done", "accepted", "linked"},
        "blocked": {"blocked"},
    }

    normalized = set()
    for raw_value in raw_values:
        normalized.update(aliases.get(raw_value, {raw_value}))
    return normalized


def _parse_filter_values(query_params, key):
    values = []
    for raw in query_params.getlist(key):
        if not raw:
            continue
        for value in str(raw).split(","):
            trimmed = value.strip()
            if trimmed:
                values.append(trimmed)
    # Keep order but remove duplicates
    deduped = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _normalize_filter_values(values):
    return [str(value).strip().lower() for value in values if str(value).strip()]


def _normalize_field_list(values):
    return [str(value).strip() for value in values if str(value).strip()]


def _has_active_search_filters(search_filters):
    return any(bool(value) for value in search_filters.values())


def _search_filters_require_record_data(search_filters):
    return any(search_filters.values())


def _search_result_matches_filters(result, object_type_filter, status_values, search_filters, user):
    if object_type_filter and (result.get("object_type_key") or "").lower() != object_type_filter.lower():
        return False
    if status_values and not _status_matches_filter(result.get("status"), status_values):
        return False
    if not _search_filters_require_record_data(search_filters):
        return False if (result.get("type") == "project" and object_type_filter == "project" and False) else True

    if result.get("type") in {"record", "document", "folder_event"}:
        record_id = result.get("record_id")
        if not record_id:
            return False
        from apps.records.models import Record

        record = Record.objects.filter(pk=record_id).first()
        if not record:
            return False
        return _record_matches_filters(record, search_filters)

    if result.get("type") == "project":
        project_id = result.get("project_id") or result.get("id")
        if project_id:
            from apps.projects.models import Project

            project = Project.objects.select_related("record").filter(pk=project_id).first()
            if project is None:
                return False
            if search_filters["project_status"]:
                if (project.status or "").lower() not in search_filters["project_status"]:
                    return False
            if _search_filters_require_record_filters_for_project(search_filters):
                if not _record_matches_filters(project.record, search_filters):
                    return False
            return True
        return False

    return True


def _search_filters_require_record_filters_for_project(search_filters):
    return bool(search_filters.get("tags") or search_filters.get("application") or search_filters.get("resin_family") or search_filters.get("color") or search_filters.get("form_fields"))


def _status_matches_filter(candidate_status, status_values):
    return (candidate_status or "").lower() in status_values


def _record_matches_filters(record, search_filters):
    if not record:
        return False

    if (
        search_filters["project_status"]
        and record.object_type_key == "project"
        and (record.status or "").lower() not in search_filters["project_status"]
    ):
        return False

    if search_filters["tags"] and not _record_data_matches(record.data, "tags", search_filters["tags"]):
        return False
    if search_filters["application"] and not _record_data_matches(record.data, "application", search_filters["application"]):
        return False
    if search_filters["resin_family"] and not _record_data_matches(record.data, "resin_family", search_filters["resin_family"]):
        return False
    if search_filters["color"] and not _record_data_matches(record.data, "color", search_filters["color"]):
        return False
    if search_filters["form_fields"] and not _record_has_form_fields(record.data, search_filters["form_fields"]):
        return False

    return True


def _record_data_matches(data, key, requested_values):
    if not requested_values:
        return True
    requested_set = {_normalize_filter_value(value) for value in requested_values}
    value = _record_data_value(data, key)
    return any(_normalize_filter_value(item) in requested_set for item in _record_data_values(value))


def _record_has_form_fields(data, field_names):
    for field_name in field_names:
        value = _record_data_value(data, field_name)
        if not _value_is_empty(value):
            return True
    return False


def _record_data_value(data, key):
    if not isinstance(data, dict):
        return None
    current = data
    for part in str(key).split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


def _record_data_values(value):
    if value is None:
        return []
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_record_data_values(item))
        return values
    return [value]


def _normalize_filter_value(value):
    if isinstance(value, bool | int | float):
        return str(value).lower().strip()
    return str(value).strip().lower()


def _value_is_empty(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return not bool(value)
    return False


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


def _authorized_project_hit(user, hit):
    from apps.projects.models import Project
    from apps.records.models import Record

    project_id = hit.get("project_id") or hit.get("id")
    if not project_id:
        return None
    project = Project.objects.select_related("record").filter(pk=project_id).first()
    if project is None:
        return None
    if not records_user_can_view(user, Record.objects.filter(pk=project.record_id)).exists():
        return None
    return hit


def _authorized_record_hit(user, hit):
    from apps.records.models import Record

    record_id = hit.get("id")
    if not record_id:
        return None
    try:
        record = Record.objects.filter(pk=record_id).first()
    except (TypeError, ValueError):
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
    except (TypeError, ValueError):
        return None
    if not event:
        return None

    record = _folder_event_record(event)
    if not record:
        if not _is_search_admin(user):
            return None
        return {
            **hit,
            "id": str(event.pk),
            "event_type": event.event_type,
            "path": event.path,
            "review_status": event.review_status,
            "object_type_key": "",
        }

    if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
        return None
    return {
        **hit,
        "id": str(event.pk),
        "event_type": event.event_type,
        "path": event.path,
        "review_status": event.review_status,
        "record_code": record.code,
        "record_title": record.title,
        "object_type_key": record.object_type_key,
        "record_id": str(record.pk),
    }


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
    except (TypeError, ValueError):
        return None
    return revision


def _folder_event_record(event):
    if event.matched_record:
        return event.matched_record
    if event.managed_folder:
        return event.managed_folder.record
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

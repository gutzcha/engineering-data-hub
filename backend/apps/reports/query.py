from __future__ import annotations

from collections import Counter
from datetime import date
import re

from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from apps.accounts.permissions import user_can
from apps.audit.models import AuditEvent
from apps.audit.views import _visible_events
from apps.documents.models import Document
from apps.projects.models import ProjectTask
from apps.records.models import Record
from apps.relationships.models import Relationship
from apps.workflows.models import WorkflowTask


DEFAULT_RESULT_LIMIT = 100
MAX_RESULT_LIMIT = 500
MAX_SCAN_LIMIT = 2000
SAFE_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)*$")
FIELD_FILTER_TYPES = {"field_equals", "field_contains", "date_before", "date_after"}
FILTER_TYPES = FIELD_FILTER_TYPES | {
    "object_type",
    "status",
    "relationship_exists",
    "assigned_workflow_task",
    "sort",
}


class ReportFilterValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Report filters are invalid.")


def saved_view_results(saved_view, user, *, limit=DEFAULT_RESULT_LIMIT):
    validate_saved_view_filters(saved_view.filters)
    queryset = apply_record_filters(Record.objects.all(), saved_view.filters, user)
    queryset = _apply_sort_fields(queryset, saved_view.sort)
    records = visible_records(
        user,
        queryset,
        limit=_bounded_limit(limit),
        filters=saved_view.filters,
    )
    return {
        "results": [_serialize_record(record, saved_view.columns) for record in records],
        "count": len(records),
    }


def validate_saved_view_filters(filters):
    if not isinstance(filters, list):
        raise ReportFilterValidationError(["Expected a list of filters."])

    errors = {}
    for index, report_filter in enumerate(filters):
        if not isinstance(report_filter, dict):
            errors[str(index)] = ["Expected a filter object."]
            continue
        filter_type = report_filter.get("type") or report_filter.get("filter")
        if filter_type not in FILTER_TYPES:
            errors[str(index)] = ["Unknown filter type."]
            continue
        if filter_type in FIELD_FILTER_TYPES:
            field = report_filter.get("field")
            if not _safe_field_key(field):
                errors[f"{index}.field"] = [
                    "Field must be a simple identifier path without Django lookup separators."
                ]
        if filter_type == "relationship_exists":
            direction = report_filter.get("direction", "either")
            if direction not in {"outgoing", "incoming", "either"}:
                errors[f"{index}.direction"] = ["Direction must be outgoing, incoming, or either."]
        if filter_type == "assigned_workflow_task" and report_filter.get("assignee_user") not in (None, ""):
            try:
                int(report_filter["assignee_user"])
            except (TypeError, ValueError):
                errors[f"{index}.assignee_user"] = ["Assignee user must be an integer ID."]
    if errors:
        raise ReportFilterValidationError(errors)


def apply_record_filters(queryset, filters, user):
    for report_filter in filters or []:
        if not isinstance(report_filter, dict):
            continue
        filter_type = report_filter.get("type") or report_filter.get("filter")
        if filter_type == "object_type":
            queryset = _filter_object_type(queryset, report_filter)
        elif filter_type == "status":
            queryset = _filter_status(queryset, report_filter)
        elif filter_type == "field_equals":
            queryset = _filter_field_lookup(queryset, report_filter, "")
        elif filter_type == "field_contains":
            queryset = _filter_field_lookup(queryset, report_filter, "__icontains")
        elif filter_type == "date_before":
            queryset = _filter_field_lookup(queryset, report_filter, "__lte")
        elif filter_type == "date_after":
            queryset = _filter_field_lookup(queryset, report_filter, "__gte")
        elif filter_type == "relationship_exists":
            queryset = _filter_relationship_exists(queryset, report_filter)
        elif filter_type == "assigned_workflow_task":
            queryset = _filter_assigned_workflow_task(queryset, report_filter, user)
    return _apply_sort(queryset, filters)


def visible_records(user, queryset, *, limit=DEFAULT_RESULT_LIMIT, filters=None):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        return []
    visible_keys = [
        key
        for key in queryset.values_list("object_type_key", flat=True).distinct()
        if user_can(user, "view", key)
    ]
    if not visible_keys:
        return []
    capped_queryset = queryset.filter(object_type_key__in=visible_keys)[: _scan_limit(limit, filters)]
    records = []
    for record in capped_queryset:
        if user_can(user, "view", record.object_type_key, record_id=str(record.pk)) and _record_matches_python_filters(
            record,
            filters,
            user,
        ):
            records.append(record)
            if limit is not None and len(records) >= limit:
                break
    return records


def run_dashboard_widget(widget, user):
    widget_type = widget.widget_type
    config = _dict_config(widget.config)
    if widget_type == "count_by_status":
        return _count_records(user, config, "status")
    if widget_type == "count_by_object_type":
        return _count_records(user, config, "object_type_key")
    if widget_type == "overdue_project_tasks":
        return _overdue_project_tasks(user, config)
    if widget_type == "missing_required_documents":
        return _missing_required_documents(user, config)
    if widget_type == "recent_changes":
        return _recent_changes(user, config)
    if widget_type == "workflow_bottlenecks":
        return _workflow_bottlenecks(user, config)
    return {"items": []}


def _filter_object_type(queryset, report_filter):
    values = _list_value(report_filter, "values") or _list_value(report_filter, "object_types")
    value = report_filter.get("value") or report_filter.get("object_type_key")
    if values:
        return queryset.filter(object_type_key__in=values)
    if value:
        return queryset.filter(object_type_key=value)
    return queryset


def _filter_status(queryset, report_filter):
    values = _list_value(report_filter, "values")
    value = report_filter.get("value") or report_filter.get("status")
    if values:
        return queryset.filter(status__in=values)
    if value:
        return queryset.filter(status=value)
    return queryset


def _filter_field_lookup(queryset, report_filter, lookup_suffix):
    field = report_filter.get("field")
    if not field:
        return queryset
    lookup = f"data__{field.replace('.', '__')}{lookup_suffix}"
    return queryset.filter(**{lookup: report_filter.get("value")})


def _filter_relationship_exists(queryset, report_filter):
    direction = report_filter.get("direction", "either")
    common_filter = Q()
    relationship_type = report_filter.get("relationship_type") or report_filter.get("relationship_type_key")
    if relationship_type:
        common_filter &= Q(relationship_type_key=relationship_type)

    related_type = report_filter.get("related_object_type_key")
    if direction == "outgoing":
        relation_filter = Q(source_record=OuterRef("pk"))
        if related_type:
            relation_filter &= Q(target_record__object_type_key=related_type)
    elif direction == "incoming":
        relation_filter = Q(target_record=OuterRef("pk"))
        if related_type:
            relation_filter &= Q(source_record__object_type_key=related_type)
    else:
        outgoing_filter = Q(source_record=OuterRef("pk"))
        incoming_filter = Q(target_record=OuterRef("pk"))
        if related_type:
            outgoing_filter &= Q(target_record__object_type_key=related_type)
            incoming_filter &= Q(source_record__object_type_key=related_type)
        relation_filter = outgoing_filter | incoming_filter
    return queryset.annotate(_has_relationship=Exists(Relationship.objects.filter(common_filter & relation_filter))).filter(
        _has_relationship=True
    )


def _filter_assigned_workflow_task(queryset, report_filter, user):
    task_filter = Q(related_record=OuterRef("pk")) | Q(instance__record=OuterRef("pk"))
    state = report_filter.get("state")
    if state:
        task_filter &= Q(state=state)
    key = report_filter.get("key") or report_filter.get("task_key")
    if key:
        task_filter &= Q(key=key)
    assignee = report_filter.get("assignee")
    if assignee in {"me", "self", "current_user"}:
        task_filter &= Q(assignee_user=user)
    elif report_filter.get("assignee_user"):
        task_filter &= Q(assignee_user_id=int(report_filter["assignee_user"]))
    assignee_role = report_filter.get("assignee_role")
    if assignee_role:
        task_filter &= Q(assignee_role=assignee_role)
    return queryset.annotate(_has_workflow_task=Exists(WorkflowTask.objects.filter(task_filter))).filter(
        _has_workflow_task=True
    )


def _apply_sort(queryset, filters):
    sort = []
    for report_filter in filters or []:
        if isinstance(report_filter, dict) and report_filter.get("type") == "sort":
            sort = report_filter.get("fields") or []
            break
    return _apply_sort_fields(queryset, sort)


def _apply_sort_fields(queryset, sort):
    allowed = {"code", "title", "status", "object_type_key", "created_at", "updated_at"}
    order_by = []
    for field in sort:
        if not isinstance(field, str):
            continue
        descending = field.startswith("-")
        clean_field = field[1:] if descending else field
        if clean_field in allowed:
            order_by.append(field)
    return queryset.order_by(*order_by) if order_by else queryset


def _count_records(user, config, field):
    queryset = apply_record_filters(Record.objects.all(), config.get("filters", []), user)
    counts = Counter(
        getattr(record, field)
        for record in visible_records(user, queryset, limit=None, filters=config.get("filters", []))
    )
    return {"items": [{"key": key, "count": counts[key]} for key in sorted(counts)]}


def _overdue_project_tasks(user, config):
    limit = _bounded_limit(config.get("limit", DEFAULT_RESULT_LIMIT))
    today = timezone.localdate()
    queryset = (
        ProjectTask.objects.select_related("project__record")
        .filter(due_date__lt=today)
        .exclude(state=ProjectTask.State.DONE)
        .order_by("due_date", "id")
    )
    items = []
    for task in queryset[: _scan_limit(limit)]:
        record = task.project.record
        if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
            continue
        items.append(
            {
                "id": task.pk,
                "title": task.title,
                "project_id": str(task.project_id),
                "project_name": task.project.name,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "state": task.state,
            }
        )
        if len(items) >= limit:
            break
    return {"items": items}


def _missing_required_documents(user, config):
    limit = _bounded_limit(config.get("limit", DEFAULT_RESULT_LIMIT))
    requirements = _document_requirements(config)
    items = []
    for requirement in requirements:
        object_type_key = requirement["object_type_key"]
        document_types = requirement["document_types"]
        if not user_can(user, "view", object_type_key):
            continue
        queryset = Record.objects.filter(object_type_key=object_type_key).order_by("code", "id")
        for record in queryset[: _scan_limit(limit)]:
            if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
                continue
            present_types = set(
                Document.objects.filter(owner_record=record, document_type__in=document_types).values_list(
                    "document_type",
                    flat=True,
                )
            )
            missing = [document_type for document_type in document_types if document_type not in present_types]
            if missing:
                items.append(
                    {
                        "record_id": str(record.pk),
                        "code": record.code,
                        "title": record.title,
                        "object_type_key": record.object_type_key,
                        "missing_document_types": missing,
                    }
                )
            if len(items) >= limit:
                return {"items": items}
    return {"items": items}


def _recent_changes(user, config):
    limit = _bounded_limit(config.get("limit", DEFAULT_RESULT_LIMIT))
    queryset = AuditEvent.objects.select_related("actor")
    events = _visible_events(user, queryset, limit=limit)
    return {
        "items": [
            {
                "id": event.pk,
                "action": event.action,
                "object_type": event.object_type,
                "object_id": event.object_id,
                "actor": event.actor_id,
                "actor_username": event.actor.username if event.actor else None,
                "created_at": _format_datetime(event.created_at),
            }
            for event in events
        ]
    }


def _workflow_bottlenecks(user, config):
    limit = _bounded_limit(config.get("limit", DEFAULT_RESULT_LIMIT))
    queryset = (
        WorkflowTask.objects.select_related("related_record", "instance__record")
        .filter(state=WorkflowTask.State.OPEN)
        .order_by("created_at", "id")
    )
    grouped = {}
    for task in queryset[:MAX_SCAN_LIMIT]:
        record = task.related_record or task.instance.record
        if not user_can(user, "view", record.object_type_key, record_id=str(record.pk)):
            continue
        key = task.key or str(task.pk)
        if len(grouped) >= limit and key not in grouped:
            break
        item = grouped.setdefault(
            key,
            {
                "key": key,
                "title": task.title,
                "state": task.state,
                "count": 0,
                "oldest_task_created_at": _format_datetime(task.created_at),
            },
        )
        item["count"] += 1
    items = sorted(grouped.values(), key=lambda item: (item["oldest_task_created_at"], item["key"]))
    return {"items": items[:limit]}


def _document_requirements(config):
    if isinstance(config.get("requirements"), list):
        return [
            {
                "object_type_key": item.get("object_type_key"),
                "document_types": _string_list(item.get("document_types")),
            }
            for item in config["requirements"]
            if isinstance(item, dict) and item.get("object_type_key") and _string_list(item.get("document_types"))
        ]
    if isinstance(config.get("required_documents"), dict):
        return [
            {"object_type_key": key, "document_types": _string_list(value)}
            for key, value in config["required_documents"].items()
            if _string_list(value)
        ]
    object_type_key = config.get("object_type_key")
    document_types = _string_list(config.get("document_types"))
    if object_type_key and document_types:
        return [{"object_type_key": object_type_key, "document_types": document_types}]
    return []


def _dict_config(value):
    return value if isinstance(value, dict) else {}


def _serialize_record(record, columns):
    payload = {
        "id": str(record.pk),
        "object_type_key": record.object_type_key,
        "code": record.code,
        "title": record.title,
        "status": record.status,
        "data": record.data,
        "created_at": _format_datetime(record.created_at),
        "updated_at": _format_datetime(record.updated_at),
    }
    if not columns:
        return payload
    selected = {"id": payload["id"]}
    for column in columns:
        if column in payload:
            selected[column] = payload[column]
        elif isinstance(column, str) and column.startswith("data."):
            field = column.split(".", 1)[1]
            selected[column] = record.data.get(field)
    return selected


def _bounded_limit(value):
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = DEFAULT_RESULT_LIMIT
    return max(1, min(limit, MAX_RESULT_LIMIT))


def _record_matches_python_filters(record, filters, user):
    for report_filter in filters or []:
        if not isinstance(report_filter, dict):
            continue
        filter_type = report_filter.get("type") or report_filter.get("filter")
        if filter_type == "relationship_exists" and not _record_has_visible_relationship(
            record,
            report_filter,
            user,
        ):
            return False
    return True


def _record_has_visible_relationship(record, report_filter, user):
    direction = report_filter.get("direction", "either")
    relationship_type = report_filter.get("relationship_type") or report_filter.get("relationship_type_key")
    related_type = report_filter.get("related_object_type_key")
    queryset = Relationship.objects.select_related("source_record", "target_record")
    if relationship_type:
        queryset = queryset.filter(relationship_type_key=relationship_type)
    if direction == "outgoing":
        queryset = queryset.filter(source_record=record)
    elif direction == "incoming":
        queryset = queryset.filter(target_record=record)
    else:
        queryset = queryset.filter(Q(source_record=record) | Q(target_record=record))

    for relationship in queryset[:MAX_SCAN_LIMIT]:
        related_record = _related_record_for_direction(record, relationship, direction)
        if related_record is None:
            continue
        if related_type and related_record.object_type_key != related_type:
            continue
        if user_can(
            user,
            "view",
            related_record.object_type_key,
            record_id=str(related_record.pk),
        ):
            return True
    return False


def _related_record_for_direction(record, relationship, direction):
    if direction == "outgoing":
        return relationship.target_record
    if direction == "incoming":
        return relationship.source_record
    if relationship.source_record_id == record.pk:
        return relationship.target_record
    if relationship.target_record_id == record.pk:
        return relationship.source_record
    return None


def _scan_limit(limit, filters=None):
    if limit is None or _has_relationship_filter(filters):
        return MAX_SCAN_LIMIT
    return min(MAX_SCAN_LIMIT, max(limit * 10, limit))


def _has_relationship_filter(filters):
    return any(
        isinstance(report_filter, dict)
        and (report_filter.get("type") or report_filter.get("filter")) == "relationship_exists"
        for report_filter in filters or []
    )


def _list_value(mapping, key):
    value = mapping.get(key)
    return _string_list(value)


def _string_list(value):
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _safe_field_key(value):
    return isinstance(value, str) and "__" not in value and SAFE_FIELD_RE.fullmatch(value) is not None


def _format_datetime(value):
    if value is None:
        return None
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value.isoformat()
    return value.isoformat().replace("+00:00", "Z")

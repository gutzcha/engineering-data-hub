from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import dateparse, timezone

from apps.documents.models import Document
from apps.records.models import Record
from apps.workflows.models import WorkflowTask


def create_tasks_for_transition(instance, transition, actor):
    tasks = []
    for template in transition.task_templates or []:
        if not isinstance(template, dict):
            continue
        task = WorkflowTask.objects.create(
            key=str(template.get("key", "")),
            instance=instance,
            title=str(template.get("title") or transition.label),
            description=str(template.get("description", "")),
            assignee_user=_resolve_assignee_user(template),
            assignee_role=str(template.get("assignee_role", "")),
            due_date=_resolve_due_date(template),
            required=template.get("required", True),
            related_record=_resolve_related_record(instance, template),
            related_document=_resolve_related_document(instance, template),
            related_project=str(template.get("related_project", "")),
            created_by=actor,
        )
        tasks.append(task)
    return tasks


def _resolve_assignee_user(template):
    assignee_user_id = template.get("assignee_user_id") or template.get("assignee_user")
    if not assignee_user_id:
        return None
    return get_user_model().objects.filter(pk=assignee_user_id).first()


def _resolve_due_date(template):
    if template.get("due_in_days") is not None:
        return timezone.now() + timedelta(days=int(template["due_in_days"]))
    due_date = template.get("due_date")
    if not due_date:
        return None
    parsed_datetime = dateparse.parse_datetime(str(due_date))
    if parsed_datetime:
        return parsed_datetime if timezone.is_aware(parsed_datetime) else timezone.make_aware(parsed_datetime)
    parsed_date = dateparse.parse_date(str(due_date))
    if parsed_date:
        return timezone.make_aware(timezone.datetime.combine(parsed_date, timezone.datetime.min.time()))
    return None


def _resolve_related_record(instance, template):
    related_record = template.get("related_record", "self")
    if related_record in {"self", None, ""}:
        return instance.record
    return Record.objects.filter(pk=related_record).first()


def _resolve_related_document(instance, template):
    related_document = template.get("related_document")
    if related_document:
        return Document.objects.filter(pk=related_document, owner_record=instance.record).first()
    document_type = template.get("related_document_type")
    if document_type:
        return Document.objects.filter(owner_record=instance.record, document_type=document_type).first()
    return None

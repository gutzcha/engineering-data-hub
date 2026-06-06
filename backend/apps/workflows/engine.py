from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.permissions import SYSTEM_ADMIN_ROLE, user_can
from apps.documents.models import Document
from apps.workflows.models import (
    WorkflowDefinition,
    WorkflowEvent,
    WorkflowInstance,
    WorkflowTask,
    WorkflowTransition,
)
from apps.workflows.tasks import create_tasks_for_transition


class WorkflowTransitionError(ValueError):
    pass


class WorkflowGuardError(WorkflowTransitionError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors))


@transaction.atomic
def perform_transition(
    instance_id: str,
    transition_key: str,
    actor_id: int,
    comment: str = "",
) -> WorkflowInstance:
    """Validate guards, update state, create tasks, emit audit, and return the updated instance."""
    actor = get_user_model().objects.get(pk=actor_id)
    instance = (
        WorkflowInstance.objects.select_for_update()
        .select_related("definition", "record")
        .get(pk=instance_id)
    )
    transition = _get_transition(instance, transition_key)
    errors = validate_guards(instance, transition, actor)
    if errors:
        raise WorkflowGuardError(errors)

    previous_state = instance.state
    instance.state = transition.to_state
    instance.updated_by = actor
    instance.save(update_fields=["state", "updated_by", "updated_at"])
    tasks = create_tasks_for_transition(instance, transition, actor)
    WorkflowEvent.objects.create(
        instance=instance,
        action="transition_performed",
        actor=actor,
        comment=comment,
        data={
            "transition_key": transition.key,
            "from_state": previous_state,
            "to_state": transition.to_state,
            "created_task_ids": [task.pk for task in tasks],
        },
    )
    return instance


def validate_guards(instance, transition, actor) -> list[str]:
    guards = transition.guards or {}
    errors = []
    errors.extend(_validate_required_fields(instance.record, guards.get("required_fields", [])))
    errors.extend(_validate_required_roles(actor, guards))
    errors.extend(_validate_required_permissions(instance.record, actor, guards))
    errors.extend(_validate_required_document_types(instance.record, guards.get("required_document_types", [])))
    errors.extend(_validate_required_tasks(instance, guards.get("required_tasks_complete")))
    return errors


def get_or_create_instance_for_record(record, actor=None):
    existing_instance = (
        WorkflowInstance.objects.select_related("definition")
        .filter(record=record)
        .exclude(state__in=["released", "done", "cancelled"])
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if existing_instance is not None:
        return existing_instance

    existing_instance = (
        WorkflowInstance.objects.select_related("definition")
        .filter(record=record)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if existing_instance is not None:
        return existing_instance

    definition = (
        WorkflowDefinition.objects.filter(object_type_key=record.object_type_key, is_active=True)
        .order_by("-version", "id")
        .first()
    )
    if definition is None:
        return None
    instance, _created = WorkflowInstance.objects.get_or_create(
        definition=definition,
        record=record,
        defaults={
            "state": definition.initial_state,
            "created_by": actor,
            "updated_by": actor,
        },
    )
    return instance


def available_transitions(instance):
    return WorkflowTransition.objects.filter(
        definition=instance.definition,
        from_state=instance.state,
    )


def _get_transition(instance, transition_key):
    transition = WorkflowTransition.objects.filter(
        definition=instance.definition,
        key=transition_key,
        from_state=instance.state,
    ).first()
    if transition is None:
        raise WorkflowTransitionError(
            f"Transition '{transition_key}' is not available from state '{instance.state}'."
        )
    return transition


def _validate_required_fields(record, required_fields):
    errors = []
    for field in required_fields or []:
        value = record.data.get(field)
        if value is None or value == "" or value == []:
            errors.append(f"Required field '{field}' is missing.")
    return errors


def _validate_required_roles(actor, guards):
    required_roles = _as_list(guards.get("required_roles", guards.get("required_role")))
    if not required_roles or actor.is_superuser:
        return []
    actor_roles = set(actor.groups.values_list("name", flat=True))
    if SYSTEM_ADMIN_ROLE in actor_roles:
        return []
    missing_roles = [role for role in required_roles if role not in actor_roles]
    if missing_roles:
        return [f"Actor must have role: {', '.join(missing_roles)}."]
    return []


def _validate_required_permissions(record, actor, guards):
    required_permissions = _as_list(
        guards.get("required_permissions", guards.get("required_permission"))
    )
    errors = []
    for permission in required_permissions:
        if not user_can(actor, permission, record.object_type_key, record_id=str(record.pk)):
            errors.append(f"Actor lacks '{permission}' permission on {record.object_type_key}.")
    return errors


def _validate_required_document_types(record, required_document_types):
    errors = []
    for document_type in required_document_types or []:
        if not Document.objects.filter(owner_record=record, document_type=document_type).exists():
            errors.append(f"Required document type '{document_type}' is missing.")
    return errors


def _validate_required_tasks(instance, required_tasks_complete):
    if required_tasks_complete in (None, False):
        return []
    if required_tasks_complete is True:
        incomplete_tasks = instance.tasks.filter(required=True).exclude(state=WorkflowTask.State.DONE)
        return [f"Required task '{task.key or task.pk}' is not complete." for task in incomplete_tasks]

    errors = []
    for task_key in _as_list(required_tasks_complete):
        incomplete_tasks = instance.tasks.filter(key=task_key, required=True).exclude(
            state=WorkflowTask.State.DONE
        )
        if incomplete_tasks.exists() or not instance.tasks.filter(key=task_key, required=True).exists():
            errors.append(f"Required task '{task_key}' is not complete.")
    return errors


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]

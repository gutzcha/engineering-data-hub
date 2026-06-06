import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class WorkflowTaskStateError(ValueError):
    pass


class WorkflowDefinition(models.Model):
    key = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=255)
    object_type_key = models.CharField(max_length=120)
    initial_state = models.CharField(max_length=80, default="draft")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["object_type_key", "is_active"]),
            models.Index(fields=["key"]),
        ]
        ordering = ["object_type_key", "key"]

    def __str__(self):
        return self.name


class WorkflowTransition(models.Model):
    definition = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    key = models.CharField(max_length=120)
    label = models.CharField(max_length=255)
    from_state = models.CharField(max_length=80)
    to_state = models.CharField(max_length=80)
    guards = models.JSONField(default=dict, blank=True)
    task_templates = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "key"],
                name="unique_workflow_transition_key",
            )
        ]
        indexes = [
            models.Index(fields=["definition", "from_state"]),
            models.Index(fields=["key"]),
        ]
        ordering = ["definition", "sort_order", "key"]

    def __str__(self):
        return f"{self.definition.key}:{self.key}"


class WorkflowInstance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    definition = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    record = models.ForeignKey(
        "records.Record",
        on_delete=models.CASCADE,
        related_name="workflow_instances",
    )
    state = models.CharField(max_length=80)
    data = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_instances_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_instances_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "record"],
                name="unique_workflow_instance_per_record_definition",
            )
        ]
        indexes = [
            models.Index(fields=["record", "state"]),
            models.Index(fields=["definition", "state"]),
        ]
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return f"{self.definition.key}:{self.record_id}:{self.state}"


class WorkflowTask(models.Model):
    class State(models.TextChoices):
        OPEN = "open", "Open"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    key = models.CharField(max_length=120, blank=True, default="")
    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    assignee_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_tasks",
    )
    assignee_role = models.CharField(max_length=120, blank=True, default="")
    due_date = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=24, choices=State.choices, default=State.OPEN)
    required = models.BooleanField(default=True)
    related_record = models.ForeignKey(
        "records.Record",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="workflow_tasks",
    )
    related_document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_tasks",
    )
    related_project = models.CharField(max_length=120, blank=True, default="")
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_tasks_completed",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_tasks_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["instance", "state"]),
            models.Index(fields=["assignee_user", "state"]),
            models.Index(fields=["assignee_role", "state"]),
            models.Index(fields=["related_record", "state"]),
        ]
        ordering = ["due_date", "created_at", "id"]

    def __str__(self):
        return self.title

    def mark_done(self, actor, comment: str = ""):
        with transaction.atomic():
            task = (
                WorkflowTask.objects.select_for_update()
                .select_related("instance")
                .get(pk=self.pk)
            )
            if task.state == self.State.DONE:
                self._copy_completion_state(task)
                return self
            if task.state == self.State.CANCELLED:
                self._copy_completion_state(task)
                raise WorkflowTaskStateError("Cancelled workflow tasks cannot be completed.")
            task.state = self.State.DONE
            task.completed_by = actor
            task.completed_at = timezone.now()
            task.save(update_fields=["state", "completed_by", "completed_at", "updated_at"])
            WorkflowEvent.objects.create(
                instance=task.instance,
                task=task,
                action="task_completed",
                actor=actor,
                comment=comment,
                data={"task_id": task.pk, "task_key": task.key},
            )
            self._copy_completion_state(task)
            return self

    def _copy_completion_state(self, task):
        self.state = task.state
        self.completed_by = task.completed_by
        self.completed_by_id = task.completed_by_id
        self.completed_at = task.completed_at


class WorkflowEvent(models.Model):
    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="events",
    )
    task = models.ForeignKey(
        WorkflowTask,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    action = models.CharField(max_length=80)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_events",
    )
    comment = models.TextField(blank=True, default="")
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["instance", "action"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.action}: {self.instance_id}"

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Project(models.Model):
    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        ACTIVE = "active", "Active"
        COMPLETE = "complete", "Complete"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.OneToOneField(
        "records.Record",
        on_delete=models.PROTECT,
        related_name="project",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PLANNING)
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_projects",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["owner", "status"]),
        ]
        ordering = ["name", "created_at"]

    def __str__(self):
        return self.name


class ProjectMilestone(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=255)
    target_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "target_date"]),
        ]
        ordering = ["target_date", "sort_order", "id"]

    def __str__(self):
        return self.title


class ProjectBoardColumn(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="board_columns")
    key = models.CharField(max_length=80)
    title = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField(default=0)
    wip_limit = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "key"],
                name="unique_project_board_column_key",
            )
        ]
        indexes = [
            models.Index(fields=["project", "sort_order"]),
        ]
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.project}: {self.title}"


class ProjectTask(models.Model):
    class State(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"
        BLOCKED = "blocked", "Blocked"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    column = models.ForeignKey(
        ProjectBoardColumn,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    milestone = models.ForeignKey(
        ProjectMilestone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    state = models.CharField(max_length=24, choices=State.choices, default=State.TODO)
    assignee_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="project_tasks",
    )
    assignee_role = models.CharField(max_length=120, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.FloatField(default=0)
    sort_order = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="project_tasks_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="project_tasks_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "state"]),
            models.Index(fields=["project", "column", "sort_order"]),
            models.Index(fields=["assignee_user", "state"]),
            models.Index(fields=["milestone"]),
            models.Index(fields=["due_date"]),
        ]
        ordering = ["sort_order", "created_at", "id"]

    def clean(self):
        if self.column_id and self.column and self.column.project_id != self.project_id:
            raise ValidationError({"column": "Column must belong to the same project."})
        if self.milestone_id and self.milestone and self.milestone.project_id != self.project_id:
            raise ValidationError({"milestone": "Milestone must belong to the same project."})

    def __str__(self):
        return self.title


class ProjectTaskDependency(models.Model):
    task = models.ForeignKey(
        ProjectTask,
        on_delete=models.CASCADE,
        related_name="dependency_edges",
    )
    depends_on = models.ForeignKey(
        ProjectTask,
        on_delete=models.CASCADE,
        related_name="dependent_edges",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="project_task_dependencies_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task", "depends_on"],
                name="unique_project_task_dependency",
            )
        ]
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["depends_on"]),
        ]
        ordering = ["task_id", "depends_on_id"]

    def clean(self):
        if self.task_id and self.task_id == self.depends_on_id:
            raise ValidationError("A task cannot depend on itself.")
        if (
            self.task_id
            and self.depends_on_id
            and self.task.project_id != self.depends_on.project_id
        ):
            raise ValidationError("Task dependencies must stay within the same project.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task_id} depends on {self.depends_on_id}"


class ProjectEvent(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="events")
    task = models.ForeignKey(
        ProjectTask,
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
        related_name="project_events",
    )
    comment = models.TextField(blank=True, default="")
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "action"]),
            models.Index(fields=["task", "action"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.action}: {self.project_id}"

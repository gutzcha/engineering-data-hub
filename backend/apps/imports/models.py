from django.conf import settings
from django.db import models


class ImportJob(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        DRY_RUN_READY = "dry_run_ready", "Dry-run ready"
        DRY_RUN_FAILED = "dry_run_failed", "Dry-run failed"
        APPLIED = "applied", "Applied"
        FAILED = "failed", "Failed"

    source_file = models.FileField(upload_to="import-jobs/", blank=True, default="")
    target_object_type = models.CharField(max_length=120)
    mapping = models.JSONField(default=dict, blank=True)
    dry_run_results = models.JSONField(default=dict, blank=True)
    created_records_count = models.PositiveIntegerField(default=0)
    updated_records_count = models.PositiveIntegerField(default=0)
    error_rows = models.JSONField(default=list, blank=True)
    state = models.CharField(max_length=32, choices=State.choices, default=State.PENDING)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="import_jobs_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="import_jobs_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["target_object_type", "state"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.target_object_type} import job {self.pk}"


class ImportAuditEvent(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"

    job = models.ForeignKey(
        ImportJob,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    record = models.ForeignKey(
        "records.Record",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="import_audit_events",
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="import_audit_events",
    )
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["record", "action"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        record_code = self.record.code if self.record else "unknown"
        return f"{self.action}: {record_code}"

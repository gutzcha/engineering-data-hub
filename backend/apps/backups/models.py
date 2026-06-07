from django.db import models


class BackupManifest(models.Model):
    class State(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    backup_id = models.CharField(max_length=120, unique=True)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    database_dump_path = models.TextField(blank=True, default="")
    managed_files_archive_path = models.TextField(blank=True, default="")
    media_archive_path = models.TextField(blank=True, default="")
    config_export_path = models.TextField(blank=True, default="")
    audit_export_path = models.TextField(blank=True, default="")
    sha256_manifest = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=24, choices=State.choices, default=State.RUNNING)
    failure_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["backup_id"], name="backups_manifest_id_idx"),
            models.Index(fields=["state", "started_at"], name="backups_manifest_state_idx"),
        ]

    def __str__(self):
        return f"{self.backup_id} ({self.state})"

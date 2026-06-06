from django.conf import settings
from django.db import models


class ManagedFolder(models.Model):
    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"

    record = models.ForeignKey(
        "records.Record",
        on_delete=models.CASCADE,
        related_name="managed_folders",
    )
    folder_role = models.CharField(max_length=80, default="primary")
    absolute_path = models.TextField()
    relative_path = models.TextField(unique=True)
    template_key = models.CharField(max_length=120)
    state = models.CharField(max_length=24, choices=State.choices, default=State.ACTIVE)
    last_scan_hash = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["record", "folder_role"],
                name="unique_managed_folder_role_per_record",
            )
        ]
        indexes = [
            models.Index(fields=["record", "folder_role"]),
            models.Index(fields=["state"]),
        ]
        ordering = ["record_id", "folder_role"]

    def __str__(self):
        return f"{self.record_id} {self.folder_role}: {self.relative_path}"


class FolderFileSnapshot(models.Model):
    managed_folder = models.ForeignKey(
        ManagedFolder,
        on_delete=models.CASCADE,
        related_name="file_snapshots",
    )
    path = models.TextField()
    file_hash = models.CharField(max_length=64)
    size = models.BigIntegerField(default=0)
    modified_ns = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["managed_folder", "path"],
                name="unique_snapshot_path_per_managed_folder",
            )
        ]
        indexes = [
            models.Index(fields=["managed_folder", "path"]),
        ]
        ordering = ["path"]

    def __str__(self):
        return self.path


class FolderChangeEvent(models.Model):
    class EventType(models.TextChoices):
        ADDED = "added", "Added"
        MODIFIED = "modified", "Modified"
        DELETED = "deleted", "Deleted"
        MOVED = "moved", "Moved"
        COLLISION = "collision", "Collision"
        LINK_REQUESTED = "link_requested", "Link requested"
        GENERATION_FAILED = "generation_failed", "Generation failed"

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        IGNORED = "ignored", "Ignored"
        LINKED = "linked", "Linked"

    event_type = models.CharField(max_length=32, choices=EventType.choices)
    path = models.TextField()
    detected_hash = models.CharField(max_length=64, blank=True, default="")
    matched_record = models.ForeignKey(
        "records.Record",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="folder_change_events",
    )
    managed_folder = models.ForeignKey(
        ManagedFolder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="change_events",
    )
    review_status = models.CharField(
        max_length=24,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_folder_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["review_status", "event_type"]),
            models.Index(fields=["managed_folder", "review_status"]),
            models.Index(fields=["matched_record", "review_status"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.event_type}: {self.path}"

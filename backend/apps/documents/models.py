from django.conf import settings
from django.db import models


class Document(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        RELEASED = "released", "Released"
        OBSOLETE = "obsolete", "Obsolete"

    title = models.CharField(max_length=255)
    owner_record = models.ForeignKey(
        "records.Record",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=120)
    current_revision = models.ForeignKey(
        "documents.DocumentRevision",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    state = models.CharField(max_length=24, choices=State.choices, default=State.DRAFT)
    folder = models.ForeignKey(
        "folders.ManagedFolder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner_record", "document_type"]),
            models.Index(fields=["state"]),
        ]
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return self.title


class DocumentRevision(models.Model):
    class ExtractionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        EXTRACTED = "extracted", "Extracted"
        UNSUPPORTED = "unsupported", "Unsupported"
        FAILED = "failed", "Failed"

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        RELEASED = "released", "Released"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision_label = models.CharField(max_length=80)
    file_name = models.CharField(max_length=255)
    storage_path = models.TextField()
    sha256 = models.CharField(max_length=64)
    size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=255, blank=True, default="")
    extracted_text = models.TextField(blank=True, default="")
    extraction_status = models.CharField(
        max_length=24,
        choices=ExtractionStatus.choices,
        default=ExtractionStatus.PENDING,
    )
    state = models.CharField(max_length=24, choices=State.choices, default=State.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="document_revisions_created",
    )
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "revision_label"],
                name="unique_revision_label_per_document",
            )
        ]
        indexes = [
            models.Index(fields=["document", "state"]),
            models.Index(fields=["sha256"]),
        ]
        ordering = ["document_id", "revision_label", "-created_at"]

    def __str__(self):
        return f"{self.document_id} {self.revision_label}"


class DocumentEvent(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="events")
    revision = models.ForeignKey(
        DocumentRevision,
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
        related_name="document_events",
    )
    data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["document", "action"]),
            models.Index(fields=["timestamp"]),
        ]
        ordering = ["-timestamp", "-id"]

    def __str__(self):
        return f"{self.action}: {self.document_id}"

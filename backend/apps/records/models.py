# ===
# File Summary
# Path: backend\apps\records\models.py
# Type: python
# Purpose: Records domain for core traceability records, validation, and coding constraints.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: Record, Status, Meta, __str__, CodeSequence
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

import uuid

from django.conf import settings
from django.db import models


class Record(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        RELEASED = "released", "Released"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    object_type_key = models.CharField(max_length=120)
    code = models.CharField(max_length=120, unique=True)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    schema_version = models.PositiveIntegerField()
    data = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="records_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="records_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["object_type_key"]),
            models.Index(fields=["code"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return f"{self.code} - {self.title}"


class CodeSequence(models.Model):
    object_type_key = models.CharField(max_length=120)
    code_pattern = models.CharField(max_length=200)
    year_scope = models.PositiveSmallIntegerField(null=True, blank=True)
    next_value = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["object_type_key", "code_pattern", "year_scope"],
                name="unique_code_sequence_scope",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["object_type_key"]),
            models.Index(fields=["code_pattern"]),
        ]

    def __str__(self):
        scope = self.year_scope if self.year_scope is not None else "global"
        return f"{self.object_type_key} {self.code_pattern} ({scope})"


class RecordObjectTypeLock(models.Model):
    object_type_key = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["object_type_key"]),
        ]

    def __str__(self):
        return f"Record write lock for {self.object_type_key}"


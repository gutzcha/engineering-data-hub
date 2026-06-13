# ===
# File Summary
# Path: backend\apps\accounts\models.py
# Type: python
# Purpose: Accounts service handling identity, roles, permissions, and authentication-facing APIs.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: ObjectPermission, Meta, __str__, RecordPermission, save
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

from django.db import models


class ObjectPermission(models.Model):
    role_name = models.CharField(max_length=120)
    object_type_key = models.CharField(max_length=120)
    can_view = models.BooleanField(default=True)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_release = models.BooleanField(default=False)
    can_admin = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role_name", "object_type_key"],
                name="unique_role_object_permission",
            )
        ]
        ordering = ["object_type_key", "role_name"]

    def __str__(self):
        return f"{self.role_name}: {self.object_type_key}"


class RecordPermission(models.Model):
    role_name = models.CharField(max_length=120)
    object_type_key = models.CharField(max_length=120)
    record = models.ForeignKey(
        "records.Record",
        on_delete=models.CASCADE,
        related_name="record_permissions",
    )
    can_view = models.BooleanField(default=True)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_release = models.BooleanField(default=False)
    can_admin = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role_name", "record"],
                name="unique_role_record_permission",
            )
        ]
        indexes = [
            models.Index(fields=["object_type_key", "record"]),
            models.Index(fields=["role_name", "object_type_key"]),
        ]
        ordering = ["object_type_key", "record_id", "role_name"]

    def save(self, *args, **kwargs):
        if self.record_id:
            self.object_type_key = self.record.object_type_key
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.role_name}: {self.object_type_key} {self.record_id}"


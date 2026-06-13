# ===
# File Summary
# Path: backend\apps\accounts\admin.py
# Type: python
# Purpose: Accounts service handling identity, roles, permissions, and authentication-facing APIs.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: ObjectPermissionAdmin, RecordPermissionAdmin
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

from django.contrib import admin

from apps.accounts.models import ObjectPermission, RecordPermission


@admin.register(ObjectPermission)
class ObjectPermissionAdmin(admin.ModelAdmin):
    list_display = (
        "role_name",
        "object_type_key",
        "can_view",
        "can_create",
        "can_edit",
        "can_release",
        "can_admin",
    )
    list_filter = ("object_type_key", "role_name")
    search_fields = ("role_name", "object_type_key")


@admin.register(RecordPermission)
class RecordPermissionAdmin(admin.ModelAdmin):
    list_display = (
        "role_name",
        "object_type_key",
        "record",
        "can_view",
        "can_create",
        "can_edit",
        "can_release",
        "can_admin",
    )
    list_filter = ("object_type_key", "role_name")
    search_fields = ("role_name", "object_type_key", "record__code", "record__title")


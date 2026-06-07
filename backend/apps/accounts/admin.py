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

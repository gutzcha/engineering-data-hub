# ===
# File Summary
# Path: backend\apps\accounts\permissions.py
# Type: python
# Purpose: Accounts service handling identity, roles, permissions, and authentication-facing APIs.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: is_system_admin, is_configuration_admin, user_can, records_user_can_view, user_has_view_scope
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

SYSTEM_ADMIN_ROLE = "System Admin"
CONFIGURATION_ADMIN_ROLE = "Configuration Admin"

ACTION_FIELDS = {
    "view": "can_view",
    "create": "can_create",
    "edit": "can_edit",
    "release": "can_release",
    "admin": "can_admin",
}


def is_system_admin(user) -> bool:
    if not _is_active_authenticated_user(user):
        return False
    return user.is_superuser or user.groups.filter(name=SYSTEM_ADMIN_ROLE).exists()


def is_configuration_admin(user) -> bool:
    if is_system_admin(user):
        return True
    if not _is_active_authenticated_user(user):
        return False
    return user.groups.filter(name=CONFIGURATION_ADMIN_ROLE).exists()


def user_can(user, action: str, object_type_key: str, record_id: str | None = None) -> bool:
    """Return True when a user has the requested action on an object type or record."""
    from django.core.exceptions import ValidationError

    from apps.accounts.models import ObjectPermission, RecordPermission

    permission_field = ACTION_FIELDS.get(action)
    if not permission_field:
        return False

    if not _is_active_authenticated_user(user):
        return False

    if is_system_admin(user):
        return True

    role_names = set(user.groups.values_list("name", flat=True))
    if record_id:
        try:
            record_permissions = RecordPermission.objects.filter(
                role_name__in=role_names,
                object_type_key=object_type_key,
                record_id=record_id,
            )
            if record_permissions.exists():
                return record_permissions.filter(**{permission_field: True}).exists()
        except (TypeError, ValueError, ValidationError):
            pass

    return ObjectPermission.objects.filter(
        role_name__in=role_names,
        object_type_key=object_type_key,
        **{permission_field: True},
    ).exists()


def records_user_can_view(user, queryset):
    """Filter a Record queryset to rows visible under object and record grants."""
    from django.db.models import Q

    from apps.accounts.models import ObjectPermission, RecordPermission

    if not _is_active_authenticated_user(user):
        return queryset.none()
    if is_system_admin(user):
        return queryset

    role_names = list(user.groups.values_list("name", flat=True))
    object_type_keys = ObjectPermission.objects.filter(
        role_name__in=role_names,
        can_view=True,
    ).values_list("object_type_key", flat=True)
    scoped_permissions = RecordPermission.objects.filter(role_name__in=role_names)
    scoped_record_ids = scoped_permissions.values_list("record_id", flat=True)
    allowed_record_ids = scoped_permissions.filter(can_view=True).values_list("record_id", flat=True)

    return queryset.filter(
        (Q(object_type_key__in=object_type_keys) & ~Q(pk__in=scoped_record_ids))
        | Q(pk__in=allowed_record_ids)
    )


def user_has_view_scope(user, object_type_key: str) -> bool:
    from apps.accounts.models import ObjectPermission, RecordPermission

    if not _is_active_authenticated_user(user):
        return False
    if is_system_admin(user):
        return True

    role_names = list(user.groups.values_list("name", flat=True))
    return (
        ObjectPermission.objects.filter(
            role_name__in=role_names,
            object_type_key=object_type_key,
            can_view=True,
        ).exists()
        or RecordPermission.objects.filter(
            role_name__in=role_names,
            object_type_key=object_type_key,
            can_view=True,
        ).exists()
    )


def _is_active_authenticated_user(user):
    return bool(user and getattr(user, "is_authenticated", False) and user.is_active)


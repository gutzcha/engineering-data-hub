SYSTEM_ADMIN_ROLE = "System Admin"

ACTION_FIELDS = {
    "view": "can_view",
    "create": "can_create",
    "edit": "can_edit",
    "release": "can_release",
    "admin": "can_admin",
}


def user_can(user, action: str, object_type_key: str, record_id: str | None = None) -> bool:
    """Return True when a user has the requested action on an object type or record."""
    from django.core.exceptions import ValidationError

    from apps.accounts.models import ObjectPermission, RecordPermission

    permission_field = ACTION_FIELDS.get(action)
    if not permission_field:
        return False

    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        return False

    if user.is_superuser:
        return True

    role_names = set(user.groups.values_list("name", flat=True))
    if SYSTEM_ADMIN_ROLE in role_names:
        return True

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

    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        return queryset.none()
    if user.is_superuser:
        return queryset

    role_names = list(user.groups.values_list("name", flat=True))
    if SYSTEM_ADMIN_ROLE in role_names:
        return queryset

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

    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True

    role_names = list(user.groups.values_list("name", flat=True))
    if SYSTEM_ADMIN_ROLE in role_names:
        return True

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

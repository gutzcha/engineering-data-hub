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
    from apps.accounts.models import ObjectPermission

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

    return ObjectPermission.objects.filter(
        role_name__in=role_names,
        object_type_key=object_type_key,
        **{permission_field: True},
    ).exists()

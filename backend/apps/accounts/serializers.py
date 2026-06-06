from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.models import ObjectPermission


class ObjectPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectPermission
        fields = [
            "id",
            "role_name",
            "object_type_key",
            "can_view",
            "can_create",
            "can_edit",
            "can_release",
            "can_admin",
        ]


class CurrentUserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ["id", "username", "email", "is_active", "is_superuser", "roles"]

    def get_roles(self, user):
        return list(user.groups.order_by("name").values_list("name", flat=True))

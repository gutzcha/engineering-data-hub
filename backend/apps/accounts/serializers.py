# ===
# File Summary
# Path: backend\apps\accounts\serializers.py
# Type: python
# Purpose: Accounts service handling identity, roles, permissions, and authentication-facing APIs.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: ObjectPermissionSerializer, Meta, RecordPermissionSerializer, CurrentUserSerializer, get_roles
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

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

from apps.accounts.models import ObjectPermission, RecordPermission


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


class RecordPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecordPermission
        fields = [
            "id",
            "role_name",
            "object_type_key",
            "record",
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


class ManagedUserSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(child=serializers.CharField(), required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_superuser",
            "roles",
            "password",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        roles = validated_data.pop("roles", [])
        password = validated_data.pop("password", "")
        user = get_user_model()(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        self._set_roles(user, roles)
        return user

    def update(self, instance, validated_data):
        roles = validated_data.pop("roles", None)
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        if roles is not None:
            self._set_roles(instance, roles)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["roles"] = list(instance.groups.order_by("name").values_list("name", flat=True))
        return data

    def _set_roles(self, user, roles):
        groups = [Group.objects.get_or_create(name=role.strip())[0] for role in roles if role.strip()]
        user.groups.set(groups)


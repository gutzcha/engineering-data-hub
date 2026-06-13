# ===
# File Summary
# Path: backend\apps\accounts\views.py
# Type: python
# Purpose: Accounts service handling identity, roles, permissions, and authentication-facing APIs.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: IsSystemAdmin, has_permission, ObjectPermissionViewSet, RecordPermissionViewSet, csrf_token
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

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.models import ObjectPermission, RecordPermission
from apps.accounts.permissions import SYSTEM_ADMIN_ROLE
from apps.accounts.serializers import (
    CurrentUserSerializer,
    ManagedUserSerializer,
    ObjectPermissionSerializer,
    RecordPermissionSerializer,
)


class IsSystemAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        return user.is_superuser or user.groups.filter(name=SYSTEM_ADMIN_ROLE).exists()


class ObjectPermissionViewSet(viewsets.ModelViewSet):
    queryset = ObjectPermission.objects.all()
    serializer_class = ObjectPermissionSerializer
    permission_classes = [IsSystemAdmin]
    filterset_fields = ["role_name", "object_type_key"]


class RecordPermissionViewSet(viewsets.ModelViewSet):
    queryset = RecordPermission.objects.select_related("record").all()
    serializer_class = RecordPermissionSerializer
    permission_classes = [IsSystemAdmin]
    filterset_fields = ["role_name", "object_type_key", "record"]


class ManagedUserViewSet(viewsets.ModelViewSet):
    serializer_class = ManagedUserSerializer
    permission_classes = [IsSystemAdmin]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        User = get_user_model()
        queryset = User.objects.filter(is_active=True).prefetch_related("groups").order_by("username", "id")
        query = (self.request.query_params.get("q") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
                | Q(groups__name__icontains=query)
            ).distinct()
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
def csrf_token(request):
    return Response({"csrfToken": get_token(request)})


@csrf_protect
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def session_login(request):
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return Response(
            {"detail": "Invalid username or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    login(request, user)
    return Response(CurrentUserSerializer(user).data, status=status.HTTP_200_OK)


@csrf_protect
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def session_logout(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    return Response(CurrentUserSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def lookup_users(request):
    query = (request.query_params.get("q") or "").strip()
    scope = (request.query_params.get("scope") or "").strip().lower()
    User = get_user_model()
    queryset = User.objects.filter(is_active=True).order_by("username", "id")

    if query:
        queryset = queryset.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    queryset = _filter_users_by_scope(queryset, scope)
    if query and not queryset.exists():
        queryset = _filter_users_by_scope(User.objects.filter(is_active=True), scope)

    return Response([_serialize_lookup_user(user) for user in queryset[:50]])


def _filter_users_by_scope(queryset, scope):
    if scope in {"assignee", "project", "project_manager", "manager"}:
        return queryset.filter(
            Q(groups__name__icontains="manager")
            | Q(groups__name__icontains="project")
            | Q(is_superuser=True),
        ).distinct()
    if scope in {"admin", "system_admin", "config_admin"}:
        return queryset.filter(
            Q(is_superuser=True)
            | Q(groups__name__icontains="system admin")
            | Q(groups__name__icontains="configuration admin"),
        ).distinct()
    return queryset


def _serialize_lookup_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "display_name": _user_display_name(user),
        "level": _user_level(user),
    }


def _user_display_name(user):
    display_name = " ".join(
        [part for part in (user.first_name.strip(), user.last_name.strip()) if part]
    ).strip()
    return display_name or user.username


def _user_level(user):
    if user.is_superuser or user.groups.filter(name="System Admin").exists():
        return "admin"

    role_names = [name.lower() for name in user.groups.values_list("name", flat=True)]
    if any("manager" in name or "project" in name for name in role_names):
        return "manager"
    if any("viewer" in name for name in role_names):
        return "viewer"
    return "operator"


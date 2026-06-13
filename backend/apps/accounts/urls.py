# ===
# File Summary
# Path: backend\apps\accounts\urls.py
# Type: python
# Purpose: Accounts service handling identity, roles, permissions, and authentication-facing APIs.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: inferred from domain responsibilities
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

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    ManagedUserViewSet,
    ObjectPermissionViewSet,
    RecordPermissionViewSet,
    lookup_users,
    csrf_token,
    current_user,
    session_login,
    session_logout,
)

router = DefaultRouter()
router.register("object-permissions", ObjectPermissionViewSet, basename="object-permission")
router.register("record-permissions", RecordPermissionViewSet, basename="record-permission")
router.register("users", ManagedUserViewSet, basename="managed-user")

urlpatterns = [
    path("csrf/", csrf_token, name="csrf-token"),
    path("login/", session_login, name="session-login"),
    path("logout/", session_logout, name="session-logout"),
    path("me/", current_user, name="current-user"),
    path("lookup/users/", lookup_users, name="lookup-users"),
    path("", include(router.urls)),
]


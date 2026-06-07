from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    ObjectPermissionViewSet,
    RecordPermissionViewSet,
    csrf_token,
    current_user,
    session_login,
    session_logout,
)

router = DefaultRouter()
router.register("object-permissions", ObjectPermissionViewSet, basename="object-permission")
router.register("record-permissions", RecordPermissionViewSet, basename="record-permission")

urlpatterns = [
    path("csrf/", csrf_token, name="csrf-token"),
    path("login/", session_login, name="session-login"),
    path("logout/", session_logout, name="session-logout"),
    path("me/", current_user, name="current-user"),
    path("", include(router.urls)),
]

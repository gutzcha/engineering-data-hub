from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import ObjectPermissionViewSet, current_user

router = DefaultRouter()
router.register("object-permissions", ObjectPermissionViewSet, basename="object-permission")

urlpatterns = [
    path("me/", current_user, name="current-user"),
    path("", include(router.urls)),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.folders.views import FolderChangeEventViewSet

router = DefaultRouter()
router.register("", FolderChangeEventViewSet, basename="folder-event")

urlpatterns = [
    path("", include(router.urls)),
]

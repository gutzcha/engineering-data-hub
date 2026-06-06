from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.records.views import RecordViewSet

router = DefaultRouter()
router.register("", RecordViewSet, basename="record")

urlpatterns = [
    path("", include(router.urls)),
]

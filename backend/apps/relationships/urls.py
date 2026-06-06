from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.relationships.views import RelationshipViewSet

router = DefaultRouter()
router.register("", RelationshipViewSet, basename="relationship")

urlpatterns = [
    path("", include(router.urls)),
]

from django.urls import path

from apps.api.views import health

urlpatterns = [
    path("api/health/", health, name="health"),
]

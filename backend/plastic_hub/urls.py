from django.urls import include, path

from apps.api.views import health

urlpatterns = [
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/config/", include("apps.config_registry.urls")),
    path("api/health/", health, name="health"),
    path("api/records/", include("apps.records.urls")),
]

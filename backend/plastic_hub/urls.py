from django.urls import include, path

from apps.api.views import health

urlpatterns = [
    path("", include("apps.workflows.urls")),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/config/", include("apps.config_registry.urls")),
    path("api/documents/", include("apps.documents.urls")),
    path("api/folder-events/", include("apps.folders.urls")),
    path("api/health/", health, name="health"),
    path("", include("apps.projects.urls")),
    path("api/records/", include("apps.records.urls")),
    path("api/relationships/", include("apps.relationships.urls")),
    path("api/search/", include("apps.search.urls")),
]

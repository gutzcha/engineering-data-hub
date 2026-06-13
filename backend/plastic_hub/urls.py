# ===
# File Summary
# Path: backend\plastic_hub\urls.py
# Type: python
# Purpose: Django project runtime configuration, routing, and process bootstrap.
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

from django.contrib import admin
from django.urls import include, path

from apps.api.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.workflows.urls")),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/backups/", include("apps.backups.urls")),
    path("api/config/", include("apps.config_registry.urls")),
    path("api/documents/", include("apps.documents.urls")),
    path("api/folder-events/", include("apps.folders.urls")),
    path("api/health/", health, name="health"),
    path("api/", include("apps.imports.urls")),
    path("", include("apps.projects.urls")),
    path("api/records/", include("apps.records.urls")),
    path("api/relationships/", include("apps.relationships.urls")),
    path("api/", include("apps.reports.urls")),
    path("api/search/", include("apps.search.urls")),
]


# ===
# File Summary
# Path: backend\apps\records\urls.py
# Type: python
# Purpose: Records domain for core traceability records, validation, and coding constraints.
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

from apps.records.views import RecordViewSet

router = DefaultRouter()
router.register("", RecordViewSet, basename="record")

urlpatterns = [
    path("", include(router.urls)),
]


# ===
# File Summary
# Path: backend\apps\documents\urls.py
# Type: python
# Purpose: Document domain service managing records, revisions, and extraction workflows.
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

from apps.documents.views import DocumentViewSet

router = DefaultRouter()
router.register("", DocumentViewSet, basename="document")

urlpatterns = [
    path("", include(router.urls)),
]


# ===
# File Summary
# Path: backend\apps\search\urls.py
# Type: python
# Purpose: Search domain for indexing payload generation and search query APIs.
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

from django.urls import path

from apps.search.views import SearchView


urlpatterns = [
    path("", SearchView.as_view(), name="search"),
]


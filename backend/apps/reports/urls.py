# ===
# File Summary
# Path: backend\apps\reports\urls.py
# Type: python
# Purpose: Reports domain for query definitions, payload shaping, and saved reporting views.
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

from apps.reports.views import (
    DashboardDetailView,
    HomeOverviewView,
    SavedViewListCreateView,
    SavedViewResultsView,
)


urlpatterns = [
    path("saved-views/", SavedViewListCreateView.as_view(), name="saved-view-list"),
    path("saved-views/<int:pk>/results/", SavedViewResultsView.as_view(), name="saved-view-results"),
    path("dashboards/home-overview/", HomeOverviewView.as_view(), name="home-overview"),
    path("dashboards/<str:identifier>/", DashboardDetailView.as_view(), name="dashboard-detail"),
]


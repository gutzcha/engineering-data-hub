from django.urls import path

from apps.reports.views import DashboardDetailView, SavedViewListCreateView, SavedViewResultsView


urlpatterns = [
    path("saved-views/", SavedViewListCreateView.as_view(), name="saved-view-list"),
    path("saved-views/<int:pk>/results/", SavedViewResultsView.as_view(), name="saved-view-results"),
    path("dashboards/<int:pk>/", DashboardDetailView.as_view(), name="dashboard-detail"),
]

from django.urls import include, path

from apps.api.views import health

urlpatterns = [
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/health/", health, name="health"),
]

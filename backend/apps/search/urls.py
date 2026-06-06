from django.urls import path

from apps.search.views import SearchView


urlpatterns = [
    path("", SearchView.as_view(), name="search"),
]

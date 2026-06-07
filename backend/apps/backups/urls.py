from django.urls import path

from apps.backups import views


urlpatterns = [
    path("", views.backup_collection, name="backup-collection"),
    path("<str:backup_id>/", views.backup_detail, name="backup-detail"),
]

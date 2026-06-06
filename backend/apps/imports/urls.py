from django.urls import path

from apps.imports.views import (
    AuditExportView,
    FolderLinkAcceptView,
    FolderScanView,
    ImportJobApplyView,
    ImportJobDryRunView,
    ImportJobListCreateView,
    ProjectStatusExportView,
    RecordsExportView,
)


urlpatterns = [
    path("imports/jobs/", ImportJobListCreateView.as_view(), name="import-job-list"),
    path("imports/jobs/<int:pk>/dry-run/", ImportJobDryRunView.as_view(), name="import-job-dry-run"),
    path("imports/jobs/<int:pk>/apply/", ImportJobApplyView.as_view(), name="import-job-apply"),
    path("imports/folder-scan/", FolderScanView.as_view(), name="folder-scan"),
    path("imports/folder-links/accept/", FolderLinkAcceptView.as_view(), name="folder-link-accept"),
    path(
        "exports/records/<str:object_type_key>.xlsx",
        RecordsExportView.as_view(),
        name="records-export",
    ),
    path("exports/audit.xlsx", AuditExportView.as_view(), name="audit-export"),
    path("exports/project-status.xlsx", ProjectStatusExportView.as_view(), name="project-status-export"),
]

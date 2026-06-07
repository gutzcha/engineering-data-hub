from django.urls import path

from apps.audit.views import AuditEventListView, DocumentAuditView, RecordAuditView

urlpatterns = [
    path("", AuditEventListView.as_view(), name="audit-list"),
    path("records/<uuid:pk>/", RecordAuditView.as_view(), name="record-audit"),
    path("documents/<int:pk>/", DocumentAuditView.as_view(), name="document-audit"),
]

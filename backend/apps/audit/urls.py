# ===
# File Summary
# Path: backend\apps\audit\urls.py
# Type: python
# Purpose: Audit service for immutable audit log capture and retrieval APIs.
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

from apps.audit.views import AuditEventListView, DocumentAuditView, RecordAuditView

urlpatterns = [
    path("", AuditEventListView.as_view(), name="audit-list"),
    path("records/<uuid:pk>/", RecordAuditView.as_view(), name="record-audit"),
    path("documents/<int:pk>/", DocumentAuditView.as_view(), name="document-audit"),
]


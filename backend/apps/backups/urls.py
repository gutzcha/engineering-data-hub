# ===
# File Summary
# Path: backend\apps\backups\urls.py
# Type: python
# Purpose: Backup service managing backup manifests, task scheduling, and restore metadata.
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

from apps.backups import views


urlpatterns = [
    path("", views.backup_collection, name="backup-collection"),
    path("<str:backup_id>/", views.backup_detail, name="backup-detail"),
]


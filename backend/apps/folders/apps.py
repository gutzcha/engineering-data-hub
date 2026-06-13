# ===
# File Summary
# Path: backend\apps\folders\apps.py
# Type: python
# Purpose: Folders domain handling templates, scans, change events, and review flows.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: FoldersConfig, ready
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

from django.apps import AppConfig


class FoldersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.folders"

    def ready(self):
        from apps.folders import signals  # noqa: F401


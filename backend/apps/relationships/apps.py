# ===
# File Summary
# Path: backend\apps\relationships\apps.py
# Type: python
# Purpose: Relationships domain for entity graph APIs and relationship operations.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: RelationshipsConfig
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


class RelationshipsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.relationships"


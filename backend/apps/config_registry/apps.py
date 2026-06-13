# ===
# File Summary
# Path: backend\apps\config_registry\apps.py
# Type: python
# Purpose: Configuration registry service for dynamic schemas, publishing, and config governance.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: ConfigRegistryConfig
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


class ConfigRegistryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.config_registry"


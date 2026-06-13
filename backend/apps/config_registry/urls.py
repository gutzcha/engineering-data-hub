# ===
# File Summary
# Path: backend\apps\config_registry\urls.py
# Type: python
# Purpose: Configuration registry service for dynamic schemas, publishing, and config governance.
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

from apps.config_registry import views

urlpatterns = [
    path("active/", views.active_config, name="config-active"),
    path("active/field-options/", views.active_field_options, name="config-active-field-options"),
    path("history/", views.config_history, name="config-history"),
    path("drafts/", views.create_draft, name="config-draft-create"),
    path("drafts/<int:draft_id>/", views.update_config_draft, name="config-draft-update"),
    path("drafts/<int:draft_id>/validate/", views.validate_config_draft, name="config-draft-validate"),
    path("drafts/<int:draft_id>/publish/", views.publish_config_draft, name="config-draft-publish"),
]


# ===
# File Summary
# Path: backend\apps\config_registry\schemas.py
# Type: python
# Purpose: Configuration registry service for dynamic schemas, publishing, and config governance.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: ConfigurationDraftSerializer, Meta, ConfigurationVersionSerializer
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

from rest_framework import serializers

from apps.config_registry.models import ConfigurationDraft, ConfigurationVersion


class ConfigurationDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigurationDraft
        fields = [
            "id",
            "data",
            "status",
            "created_by",
            "updated_by",
            "published_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "created_by",
            "updated_by",
            "published_version",
            "created_at",
            "updated_at",
        ]


class ConfigurationVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigurationVersion
        fields = ["id", "version", "data", "published_by", "published_at"]
        read_only_fields = fields


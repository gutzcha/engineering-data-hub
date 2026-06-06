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

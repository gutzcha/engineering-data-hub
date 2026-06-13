# ===
# File Summary
# Path: backend\apps\folders\serializers.py
# Type: python
# Purpose: Folders domain handling templates, scans, change events, and review flows.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: FolderChangeEventSerializer, Meta, get_assignee_username, get_reviewer_username
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

from apps.folders.models import FolderChangeEvent


class FolderChangeEventSerializer(serializers.ModelSerializer):
    assignee = serializers.IntegerField(source="assigned_to_id", read_only=True)
    assignee_username = serializers.SerializerMethodField()
    reviewer_username = serializers.SerializerMethodField()

    class Meta:
        model = FolderChangeEvent
        fields = [
            "id",
            "event_type",
            "path",
            "detected_hash",
            "matched_record",
            "managed_folder",
            "review_status",
            "reviewer",
            "reviewer_username",
            "assigned_to",
            "assignee",
            "assignee_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_assignee_username(self, obj):
        return obj.assigned_to.username if obj.assigned_to else None

    def get_reviewer_username(self, obj):
        return obj.reviewer.username if obj.reviewer else None


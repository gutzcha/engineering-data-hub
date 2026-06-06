from rest_framework import serializers

from apps.folders.models import FolderChangeEvent


class FolderChangeEventSerializer(serializers.ModelSerializer):
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

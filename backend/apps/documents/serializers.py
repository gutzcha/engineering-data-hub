from rest_framework import serializers

from apps.documents.models import Document, DocumentEvent, DocumentRevision


class DocumentRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRevision
        fields = [
            "id",
            "revision_label",
            "file_name",
            "sha256",
            "size",
            "mime_type",
            "extraction_status",
            "state",
            "created_by",
            "released_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
    current_revision = DocumentRevisionSerializer(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "owner_record",
            "document_type",
            "current_revision",
            "state",
            "folder",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "current_revision", "state", "created_at", "updated_at"]


class DocumentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentEvent
        fields = ["id", "document", "revision", "action", "actor", "data", "timestamp"]
        read_only_fields = fields

# ===
# File Summary
# Path: backend\apps\documents\serializers.py
# Type: python
# Purpose: Document domain service managing records, revisions, and extraction workflows.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: DocumentRevisionSerializer, Meta, DocumentSerializer, DocumentEventSerializer
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
    revisions = DocumentRevisionSerializer(many=True, read_only=True)
    owner_record_code = serializers.SerializerMethodField()
    owner_record_title = serializers.SerializerMethodField()
    owner_record_object_type = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    audit_url = serializers.SerializerMethodField()
    revision_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "owner_record",
            "owner_record_code",
            "owner_record_title",
            "owner_record_object_type",
            "document_type",
            "current_revision",
            "revisions",
            "state",
            "folder",
            "preview_url",
            "download_url",
            "audit_url",
            "revision_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "current_revision", "state", "created_at", "updated_at"]

    def get_owner_record_code(self, obj):
        return obj.owner_record.code if obj.owner_record_id else ""

    def get_owner_record_title(self, obj):
        return obj.owner_record.title if obj.owner_record_id else ""

    def get_owner_record_object_type(self, obj):
        return obj.owner_record.object_type_key if obj.owner_record_id else ""

    def get_preview_url(self, obj):
        return f"/api/documents/{obj.pk}/preview/"

    def get_download_url(self, obj):
        return f"/api/documents/{obj.pk}/download/"

    def get_audit_url(self, obj):
        return f"/api/documents/{obj.pk}/audit/"

    def get_revision_count(self, obj):
        return obj.revisions.count()


class DocumentSummarySerializer(serializers.ModelSerializer):
    current_revision = DocumentRevisionSerializer(read_only=True)
    owner_record_code = serializers.SerializerMethodField()
    owner_record_title = serializers.SerializerMethodField()
    owner_record_object_type = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    audit_url = serializers.SerializerMethodField()
    revision_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "owner_record",
            "owner_record_code",
            "owner_record_title",
            "owner_record_object_type",
            "document_type",
            "current_revision",
            "state",
            "folder",
            "preview_url",
            "download_url",
            "audit_url",
            "revision_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_owner_record_code(self, obj):
        return obj.owner_record.code if obj.owner_record_id else ""

    def get_owner_record_title(self, obj):
        return obj.owner_record.title if obj.owner_record_id else ""

    def get_owner_record_object_type(self, obj):
        return obj.owner_record.object_type_key if obj.owner_record_id else ""

    def get_preview_url(self, obj):
        return f"/api/documents/{obj.pk}/preview/"

    def get_download_url(self, obj):
        return f"/api/documents/{obj.pk}/download/"

    def get_audit_url(self, obj):
        return f"/api/documents/{obj.pk}/audit/"

    def get_revision_count(self, obj):
        return obj.revisions.count()


class DocumentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentEvent
        fields = ["id", "document", "revision", "action", "actor", "data", "timestamp"]
        read_only_fields = fields


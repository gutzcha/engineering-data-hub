# ===
# File Summary
# Path: backend\apps\projects\serializers.py
# Type: python
# Purpose: Projects domain for entity lifecycle and dependency graph orchestration.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: ProjectTaskSerializer, Meta, ProjectTaskDependencySerializer
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

from apps.projects.models import Project, ProjectTask, ProjectTaskDependency


class ProjectListSerializer(serializers.ModelSerializer):
    record = serializers.SerializerMethodField()
    record_code = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "status",
            "description",
            "record",
            "record_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_record(self, obj):
        return str(obj.record_id)

    def get_record_code(self, obj):
        return str(getattr(obj.record, "code", ""))


class ProjectTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTask
        fields = [
            "id",
            "project",
            "column",
            "milestone",
            "title",
            "description",
            "state",
            "assignee_user",
            "assignee_role",
            "start_date",
            "due_date",
            "estimated_hours",
            "sort_order",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProjectTaskDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTaskDependency
        fields = ["id", "task", "depends_on", "created_by", "created_at"]
        read_only_fields = fields


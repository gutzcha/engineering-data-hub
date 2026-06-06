from rest_framework import serializers

from apps.projects.models import ProjectTask, ProjectTaskDependency


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

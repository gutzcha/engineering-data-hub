from rest_framework import serializers

from django.contrib.auth import get_user_model

from apps.projects.models import Project, ProjectTask, ProjectTaskDependency
from apps.projects.models import ProjectEvent


User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True, default=None)
    task_count = serializers.SerializerMethodField()
    open_tasks = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "record",
            "name",
            "description",
            "status",
            "owner",
            "owner_username",
            "start_date",
            "target_date",
            "task_count",
            "open_tasks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_task_count(self, project):
        return getattr(project, "task_count", None) or project.tasks.count()

    def get_open_tasks(self, project):
        annotated_count = getattr(project, "open_tasks", None)
        if annotated_count is not None:
            return annotated_count
        return project.tasks.exclude(state=ProjectTask.State.DONE).count()


class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    target_date = serializers.DateField(required=False, allow_null=True)
    data = serializers.JSONField(required=False)

    def validate_data(self, value):
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Expected an object.")
        return value


class ProjectUpdateSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Project.Status.choices, required=False)
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    target_date = serializers.DateField(required=False, allow_null=True)


class ProjectTaskUpdateSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=ProjectTask.State.choices, required=False)
    assignee_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    due_date = serializers.DateField(required=False, allow_null=True)
    estimated_hours = serializers.FloatField(required=False, min_value=0)


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


class ProjectEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, default=None)
    task_title = serializers.CharField(source="task.title", read_only=True, default=None)

    class Meta:
        model = ProjectEvent
        fields = [
            "id",
            "project",
            "task",
            "task_title",
            "action",
            "actor",
            "actor_username",
            "comment",
            "data",
            "created_at",
        ]
        read_only_fields = fields

# ===
# File Summary
# Path: backend\apps\projects\migrations\0001_initial.py
# Type: python
# Purpose: Projects domain for entity lifecycle and dependency graph orchestration.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: Migration
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

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("records", "0002_recordobjecttypelock"),
    ]

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("planning", "Planning"),
                            ("active", "Active"),
                            ("complete", "Complete"),
                            ("archived", "Archived"),
                        ],
                        default="planning",
                        max_length=24,
                    ),
                ),
                ("start_date", models.DateField(blank=True, null=True)),
                ("target_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="projects_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_projects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "record",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="project",
                        to="records.record",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="projects_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["name", "created_at"],
                "indexes": [
                    models.Index(fields=["status"], name="projects_pr_status_f023cb_idx"),
                    models.Index(fields=["owner", "status"], name="projects_pr_owner_i_4798b7_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProjectMilestone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("target_date", models.DateField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="milestones",
                        to="projects.project",
                    ),
                ),
            ],
            options={
                "ordering": ["target_date", "sort_order", "id"],
                "indexes": [
                    models.Index(fields=["project", "target_date"], name="projects_pr_project_227d85_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProjectBoardColumn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=80)),
                ("title", models.CharField(max_length=255)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("wip_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="board_columns",
                        to="projects.project",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "id"],
                "indexes": [
                    models.Index(fields=["project", "sort_order"], name="projects_pr_project_edb44f_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("project", "key"),
                        name="unique_project_board_column_key",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ProjectTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("todo", "To Do"),
                            ("in_progress", "In Progress"),
                            ("done", "Done"),
                            ("blocked", "Blocked"),
                        ],
                        default="todo",
                        max_length=24,
                    ),
                ),
                ("assignee_role", models.CharField(blank=True, default="", max_length=120)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("estimated_hours", models.FloatField(default=0)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assignee_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="project_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "column",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tasks",
                        to="projects.projectboardcolumn",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="project_tasks_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "milestone",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tasks",
                        to="projects.projectmilestone",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to="projects.project",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="project_tasks_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "created_at", "id"],
                "indexes": [
                    models.Index(fields=["project", "state"], name="projects_pr_project_c7685c_idx"),
                    models.Index(fields=["project", "column", "sort_order"], name="projects_pr_project_7a22ef_idx"),
                    models.Index(fields=["assignee_user", "state"], name="projects_pr_assigne_923e8c_idx"),
                    models.Index(fields=["milestone"], name="projects_pr_milesto_36a531_idx"),
                    models.Index(fields=["due_date"], name="projects_pr_due_dat_31c46b_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProjectEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=80)),
                ("comment", models.TextField(blank=True, default="")),
                ("data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="project_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="projects.project",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="events",
                        to="projects.projecttask",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["project", "action"], name="projects_pr_project_bb25ec_idx"),
                    models.Index(fields=["task", "action"], name="projects_pr_task_id_cfaae0_idx"),
                    models.Index(fields=["created_at"], name="projects_pr_created_6bf26b_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProjectTaskDependency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="project_task_dependencies_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "depends_on",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dependent_edges",
                        to="projects.projecttask",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dependency_edges",
                        to="projects.projecttask",
                    ),
                ),
            ],
            options={
                "ordering": ["task_id", "depends_on_id"],
                "indexes": [
                    models.Index(fields=["task"], name="projects_pr_task_id_bb282e_idx"),
                    models.Index(fields=["depends_on"], name="projects_pr_depends_f91d10_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("task", "depends_on"),
                        name="unique_project_task_dependency",
                    )
                ],
            },
        ),
    ]


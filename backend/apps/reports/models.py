# ===
# File Summary
# Path: backend\apps\reports\models.py
# Type: python
# Purpose: Reports domain for query definitions, payload shaping, and saved reporting views.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: SavedView, Meta, __str__, Dashboard, DashboardWidget
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

from django.conf import settings
from django.db import models


class SavedView(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_views",
    )
    filters = models.JSONField(default=list, blank=True)
    columns = models.JSONField(default=list, blank=True)
    sort = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "name"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Dashboard(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dashboards",
    )
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class DashboardWidget(models.Model):
    class WidgetType(models.TextChoices):
        COUNT_BY_STATUS = "count_by_status", "Count by status"
        COUNT_BY_OBJECT_TYPE = "count_by_object_type", "Count by object type"
        OVERDUE_PROJECT_TASKS = "overdue_project_tasks", "Overdue project tasks"
        MISSING_REQUIRED_DOCUMENTS = "missing_required_documents", "Missing required documents"
        RECENT_CHANGES = "recent_changes", "Recent changes"
        WORKFLOW_BOTTLENECKS = "workflow_bottlenecks", "Workflow bottlenecks"

    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name="widgets",
    )
    title = models.CharField(max_length=255)
    widget_type = models.CharField(max_length=80, choices=WidgetType.choices)
    config = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["dashboard", "sort_order"]),
            models.Index(fields=["widget_type"]),
        ]
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.dashboard}: {self.title}"


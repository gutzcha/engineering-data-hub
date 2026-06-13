# ===
# File Summary
# Path: backend\apps\projects\urls.py
# Type: python
# Purpose: Projects domain for entity lifecycle and dependency graph orchestration.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: inferred from domain responsibilities
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

from django.urls import path

from apps.projects.views import (
    ProjectListView,
    ProjectBoardView,
    ProjectTaskDependencyView,
    ProjectTaskMoveView,
    ProjectTimelineView,
    ProjectWorkloadView,
)

urlpatterns = [
    path("api/projects/", ProjectListView.as_view(), name="project-list"),
    path("api/projects/workload/", ProjectWorkloadView.as_view(), name="project-workload"),
    path("api/projects/<uuid:project_id>/board/", ProjectBoardView.as_view(), name="project-board"),
    path(
        "api/projects/<uuid:project_id>/timeline/",
        ProjectTimelineView.as_view(),
        name="project-timeline",
    ),
    path(
        "api/project-tasks/<int:pk>/move/",
        ProjectTaskMoveView.as_view(),
        name="project-task-move",
    ),
    path(
        "api/project-tasks/<int:pk>/dependencies/",
        ProjectTaskDependencyView.as_view(),
        name="project-task-dependencies",
    ),
]


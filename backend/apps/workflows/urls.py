# ===
# File Summary
# Path: backend\apps\workflows\urls.py
# Type: python
# Purpose: Workflow domain for task models, engine execution, and worker scheduling.
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

from apps.workflows.views import (
    RecordWorkflowTransitionView,
    RecordWorkflowView,
    WorkflowTaskCompleteView,
    WorkflowTaskListView,
)

urlpatterns = [
    path("api/workflow-tasks/", WorkflowTaskListView.as_view(), name="workflow-task-list"),
    path(
        "api/workflow-tasks/<int:pk>/complete/",
        WorkflowTaskCompleteView.as_view(),
        name="workflow-task-complete",
    ),
    path("api/records/<uuid:record_id>/workflow/", RecordWorkflowView.as_view(), name="record-workflow"),
    path(
        "api/records/<uuid:record_id>/workflow/<str:transition_key>/",
        RecordWorkflowTransitionView.as_view(),
        name="record-workflow-transition",
    ),
]


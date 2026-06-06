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

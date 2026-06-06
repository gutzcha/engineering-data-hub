from django.urls import path

from apps.projects.views import (
    ProjectBoardView,
    ProjectTaskDependencyView,
    ProjectTaskMoveView,
    ProjectTimelineView,
    ProjectWorkloadView,
)

urlpatterns = [
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

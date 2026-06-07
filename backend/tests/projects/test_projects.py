import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.models import ObjectPermission, RecordPermission
from apps.config_registry.seed import starter_configuration_data
from apps.config_registry.services import create_draft_from_current, publish_draft
from apps.records.models import Record


@pytest.fixture
def user_factory(db):
    User = get_user_model()

    def create_user(username, role_name=None):
        user = User.objects.create_user(username=username, password="test-pass")
        if role_name:
            group, _created = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)
        return user

    return create_user


@pytest.fixture
def active_project_config(user_factory):
    user = user_factory("project-config-publisher")
    draft = create_draft_from_current(user)
    draft.data = starter_configuration_data()
    draft.save()
    return publish_draft(draft, user)


@pytest.fixture
def project_permissions(db):
    ObjectPermission.objects.create(
        role_name="Project Viewer",
        object_type_key="project",
        can_view=True,
    )
    ObjectPermission.objects.create(
        role_name="Project Manager",
        object_type_key="project",
        can_view=True,
        can_create=True,
        can_edit=True,
    )


def post_json(client, path, payload):
    return client.post(path, payload, content_type="application/json")


def patch_json(client, path, payload):
    return client.patch(path, payload, content_type="application/json")


def create_project(name, actor):
    try:
        from apps.projects.services import create_project
    except ModuleNotFoundError:
        pytest.fail("projects service is missing")
    return create_project(name=name, actor=actor)


def project_models():
    try:
        from apps.projects.models import (
            ProjectBoardColumn,
            ProjectEvent,
            ProjectTask,
        )
    except ModuleNotFoundError:
        pytest.fail("projects models are missing")
    return ProjectBoardColumn, ProjectEvent, ProjectTask


@pytest.mark.django_db
def test_create_project_creates_generic_project_record(
    user_factory,
    active_project_config,
    project_permissions,
):
    actor = user_factory("project-creator", "Project Manager")

    project = create_project("Line Trial", actor)

    assert project.record.object_type_key == "project"
    assert project.record.code == "PRJ-000001"
    assert project.record.title == "Line Trial"
    assert project.record.data["project_name"] == "Line Trial"
    assert project.record.data["project_type"] == "New Product"
    assert project.record.schema_version == active_project_config.version
    assert project.record.created_by == actor
    assert Record.objects.filter(pk=project.record_id, object_type_key="project").exists()


@pytest.mark.django_db
def test_create_project_enqueues_record_search_indexing(
    user_factory,
    active_project_config,
    project_permissions,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    from apps.search import tasks

    actor = user_factory("project-index-creator", "Project Manager")
    indexed_record_ids = []
    monkeypatch.setattr(tasks.index_record, "delay", lambda record_id: indexed_record_ids.append(record_id))

    with django_capture_on_commit_callbacks(execute=True):
        project = create_project("Indexed Project", actor)

    assert indexed_record_ids == [str(project.record_id)]


@pytest.mark.django_db
def test_board_groups_tasks_by_columns_and_move_records_event(
    client,
    user_factory,
    active_project_config,
    project_permissions,
):
    ProjectBoardColumn, ProjectEvent, ProjectTask = project_models()
    manager = user_factory("board-manager", "Project Manager")
    project = create_project("Board Project", manager)
    todo = ProjectBoardColumn.objects.create(project=project, key="todo", title="To Do", sort_order=1)
    doing = ProjectBoardColumn.objects.create(project=project, key="doing", title="Doing", sort_order=2)
    task = ProjectTask.objects.create(
        project=project,
        column=todo,
        title="Prepare resin blend",
        estimated_hours=4,
        sort_order=10,
    )
    ProjectTask.objects.create(
        project=project,
        column=doing,
        title="Run first extrusion pass",
        estimated_hours=6,
        sort_order=5,
    )
    client.force_login(manager)

    board_response = client.get(f"/api/projects/{project.pk}/board/")
    move_response = patch_json(
        client,
        f"/api/project-tasks/{task.pk}/move/",
        {"column": doing.pk, "sort_order": 1},
    )
    moved_board_response = client.get(f"/api/projects/{project.pk}/board/")

    assert board_response.status_code == 200
    columns = board_response.json()["columns"]
    assert [column["key"] for column in columns] == ["todo", "doing"]
    assert [item["title"] for item in columns[0]["tasks"]] == ["Prepare resin blend"]
    assert [item["title"] for item in columns[1]["tasks"]] == ["Run first extrusion pass"]
    assert move_response.status_code == 200
    assert move_response.json()["column"] == doing.pk
    assert move_response.json()["sort_order"] == 1
    assert moved_board_response.json()["columns"][0]["tasks"] == []
    assert [item["title"] for item in moved_board_response.json()["columns"][1]["tasks"]] == [
        "Prepare resin blend",
        "Run first extrusion pass",
    ]
    assert ProjectEvent.objects.filter(
        project=project,
        task=task,
        action="task_moved",
        actor=manager,
        data__from_column=todo.pk,
        data__to_column=doing.pk,
    ).exists()


@pytest.mark.django_db
def test_move_rejects_negative_sort_order_without_mutating_task(
    client,
    user_factory,
    active_project_config,
    project_permissions,
):
    ProjectBoardColumn, ProjectEvent, ProjectTask = project_models()
    manager = user_factory("negative-sort-manager", "Project Manager")
    project = create_project("Negative Sort Project", manager)
    todo = ProjectBoardColumn.objects.create(project=project, key="todo", title="To Do", sort_order=1)
    doing = ProjectBoardColumn.objects.create(project=project, key="doing", title="Doing", sort_order=2)
    task = ProjectTask.objects.create(
        project=project,
        column=todo,
        title="Stay put",
        sort_order=10,
    )
    client.force_login(manager)

    response = patch_json(
        client,
        f"/api/project-tasks/{task.pk}/move/",
        {"column": doing.pk, "sort_order": -1},
    )

    assert response.status_code == 400
    assert response.json()["sort_order"] == ["Must be greater than or equal to 0."]
    task.refresh_from_db()
    assert task.column == todo
    assert task.sort_order == 10
    assert ProjectEvent.objects.filter(task=task, action="task_moved").exists() is False


@pytest.mark.django_db
def test_timeline_returns_milestones_tasks_and_dependency_edges(
    client,
    user_factory,
    active_project_config,
    project_permissions,
):
    from datetime import date

    try:
        from apps.projects.models import (
            ProjectMilestone,
            ProjectTaskDependency,
        )
    except ModuleNotFoundError:
        pytest.fail("projects models are missing")
    _ProjectBoardColumn, _ProjectEvent, ProjectTask = project_models()
    manager = user_factory("timeline-manager", "Project Manager")
    project = create_project("Timeline Project", manager)
    milestone = ProjectMilestone.objects.create(
        project=project,
        title="Pilot Complete",
        target_date=date(2026, 7, 15),
    )
    prepare = ProjectTask.objects.create(
        project=project,
        title="Prepare DOE",
        start_date=date(2026, 7, 1),
        due_date=date(2026, 7, 3),
        milestone=milestone,
    )
    run = ProjectTask.objects.create(
        project=project,
        title="Run pilot",
        start_date=date(2026, 7, 4),
        due_date=date(2026, 7, 10),
    )
    ProjectTaskDependency.objects.create(task=run, depends_on=prepare)
    client.force_login(manager)

    response = client.get(f"/api/projects/{project.pk}/timeline/")

    assert response.status_code == 200
    body = response.json()
    assert body["project"]["id"] == str(project.pk)
    assert body["milestones"] == [
        {
            "id": milestone.pk,
            "title": "Pilot Complete",
            "target_date": "2026-07-15",
            "completed_at": None,
        }
    ]
    assert [task["title"] for task in body["tasks"]] == ["Prepare DOE", "Run pilot"]
    assert body["tasks"][0]["milestone"] == milestone.pk
    assert body["dependencies"] == [{"task": run.pk, "depends_on": prepare.pk}]


@pytest.mark.django_db
def test_task_dependency_save_rejects_cross_project_edges(
    user_factory,
    active_project_config,
    project_permissions,
):
    try:
        from apps.projects.models import ProjectTaskDependency
    except ModuleNotFoundError:
        pytest.fail("projects models are missing")
    _ProjectBoardColumn, _ProjectEvent, ProjectTask = project_models()
    manager = user_factory("cross-project-manager", "Project Manager")
    first_project = create_project("First Cross Project", manager)
    second_project = create_project("Second Cross Project", manager)
    first_task = ProjectTask.objects.create(project=first_project, title="First task")
    second_task = ProjectTask.objects.create(project=second_project, title="Second task")

    with pytest.raises(ValidationError, match="same project"):
        ProjectTaskDependency.objects.create(task=first_task, depends_on=second_task)


@pytest.mark.django_db
def test_timeline_excludes_cross_project_dependency_rows_created_outside_model_save(
    client,
    user_factory,
    active_project_config,
    project_permissions,
):
    try:
        from apps.projects.models import ProjectTaskDependency
    except ModuleNotFoundError:
        pytest.fail("projects models are missing")
    _ProjectBoardColumn, _ProjectEvent, ProjectTask = project_models()
    manager = user_factory("timeline-cross-project-manager", "Project Manager")
    first_project = create_project("Timeline First Cross Project", manager)
    second_project = create_project("Timeline Second Cross Project", manager)
    first_task = ProjectTask.objects.create(project=first_project, title="First task")
    second_task = ProjectTask.objects.create(project=second_project, title="Second task")
    ProjectTaskDependency.objects.bulk_create(
        [ProjectTaskDependency(task=first_task, depends_on=second_task)]
    )
    client.force_login(manager)

    response = client.get(f"/api/projects/{first_project.pk}/timeline/")

    assert response.status_code == 200
    assert response.json()["dependencies"] == []


@pytest.mark.django_db
def test_project_workload_respects_record_level_project_visibility(
    client,
    user_factory,
    active_project_config,
    project_permissions,
):
    _ProjectBoardColumn, _ProjectEvent, ProjectTask = project_models()
    manager = user_factory("workload-manager", "Project Manager")
    assignee = user_factory("workload-assignee")
    visible_project = create_project("Visible Workload Project", manager)
    hidden_project = create_project("Hidden Workload Project", manager)
    ProjectTask.objects.create(
        project=visible_project,
        title="Visible workload task",
        state=ProjectTask.State.IN_PROGRESS,
        assignee_user=assignee,
        estimated_hours=3,
    )
    ProjectTask.objects.create(
        project=hidden_project,
        title="Hidden workload task",
        state=ProjectTask.State.IN_PROGRESS,
        assignee_user=assignee,
        estimated_hours=5,
    )
    RecordPermission.objects.create(
        role_name="Project Viewer",
        object_type_key="project",
        record=hidden_project.record,
        can_view=False,
    )
    client.force_login(user_factory("workload-viewer", "Project Viewer"))

    response = client.get("/api/projects/workload/")

    assert response.status_code == 200
    assert response.json() == [
        {
            "assignee_user": assignee.pk,
            "username": assignee.username,
            "open_tasks": 1,
            "estimated_hours": 3.0,
        }
    ]


@pytest.mark.django_db
def test_project_workload_allows_record_scoped_project_viewer(
    client,
    user_factory,
    active_project_config,
    project_permissions,
):
    _ProjectBoardColumn, _ProjectEvent, ProjectTask = project_models()
    manager = user_factory("scoped-workload-manager", "Project Manager")
    assignee = user_factory("scoped-workload-assignee")
    visible_project = create_project("Scoped Visible Workload Project", manager)
    hidden_project = create_project("Scoped Hidden Workload Project", manager)
    ProjectTask.objects.create(
        project=visible_project,
        title="Visible scoped workload task",
        state=ProjectTask.State.IN_PROGRESS,
        assignee_user=assignee,
        estimated_hours=4,
    )
    ProjectTask.objects.create(
        project=hidden_project,
        title="Hidden scoped workload task",
        state=ProjectTask.State.IN_PROGRESS,
        assignee_user=assignee,
        estimated_hours=7,
    )
    RecordPermission.objects.create(
        role_name="Scoped Project Workload Viewer",
        object_type_key="project",
        record=visible_project.record,
        can_view=True,
    )
    client.force_login(user_factory("scoped-workload-viewer", "Scoped Project Workload Viewer"))

    response = client.get("/api/projects/workload/")

    assert response.status_code == 200
    assert response.json() == [
        {
            "assignee_user": assignee.pk,
            "username": assignee.username,
            "open_tasks": 1,
            "estimated_hours": 4.0,
        }
    ]

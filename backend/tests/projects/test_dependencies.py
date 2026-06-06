import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.models import ObjectPermission
from apps.config_registry.seed import starter_configuration_data
from apps.config_registry.services import create_draft_from_current, publish_draft


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
    user = user_factory("dependency-config-publisher")
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


def create_project(name, actor):
    try:
        from apps.projects.services import create_project
    except ModuleNotFoundError:
        pytest.fail("projects service is missing")
    return create_project(name=name, actor=actor)


def project_task_model():
    try:
        from apps.projects.models import ProjectTask
    except ModuleNotFoundError:
        pytest.fail("projects models are missing")
    return ProjectTask


@pytest.mark.django_db
def test_dependency_api_rejects_self_dependency(
    client,
    user_factory,
    active_project_config,
    project_permissions,
):
    manager = user_factory("self-dependency-manager", "Project Manager")
    project = create_project("Self Dependency Project", manager)
    ProjectTask = project_task_model()
    task = ProjectTask.objects.create(project=project, title="Compound material")
    client.force_login(manager)

    response = post_json(
        client,
        f"/api/project-tasks/{task.pk}/dependencies/",
        {"depends_on": task.pk},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "A task cannot depend on itself."


@pytest.mark.django_db
def test_dependency_api_rejects_circular_dependency(
    client,
    user_factory,
    active_project_config,
    project_permissions,
):
    manager = user_factory("cycle-manager", "Project Manager")
    project = create_project("Cycle Project", manager)
    ProjectTask = project_task_model()
    first = ProjectTask.objects.create(project=project, title="First pass")
    second = ProjectTask.objects.create(project=project, title="Second pass")
    third = ProjectTask.objects.create(project=project, title="Third pass")
    client.force_login(manager)

    assert post_json(
        client,
        f"/api/project-tasks/{second.pk}/dependencies/",
        {"depends_on": first.pk},
    ).status_code == 201
    assert post_json(
        client,
        f"/api/project-tasks/{third.pk}/dependencies/",
        {"depends_on": second.pk},
    ).status_code == 201
    response = post_json(
        client,
        f"/api/project-tasks/{first.pk}/dependencies/",
        {"depends_on": third.pk},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Circular task dependencies are not allowed."


@pytest.mark.django_db
def test_completed_tasks_can_remain_dependencies_and_workload_counts_open_work(
    client,
    user_factory,
    active_project_config,
    project_permissions,
):
    manager = user_factory("workload-manager", "Project Manager")
    assignee = user_factory("workload-engineer", "Project Manager")
    project = create_project("Workload Project", manager)
    ProjectTask = project_task_model()
    done = ProjectTask.objects.create(
        project=project,
        title="Completed prerequisite",
        state=ProjectTask.State.DONE,
        estimated_hours=8,
        assignee_user=assignee,
    )
    open_task = ProjectTask.objects.create(
        project=project,
        title="Open follow-up",
        estimated_hours=3.5,
        assignee_user=assignee,
    )
    client.force_login(manager)

    dependency_response = post_json(
        client,
        f"/api/project-tasks/{open_task.pk}/dependencies/",
        {"depends_on": done.pk},
    )
    workload_response = client.get("/api/projects/workload/")

    assert dependency_response.status_code == 201
    assert dependency_response.json()["task"] == open_task.pk
    assert dependency_response.json()["depends_on"] == done.pk
    assert workload_response.status_code == 200
    assert workload_response.json() == [
        {
            "assignee_user": assignee.pk,
            "username": "workload-engineer",
            "open_tasks": 1,
            "estimated_hours": 3.5,
        }
    ]


@pytest.mark.django_db
def test_dependency_creation_locks_project_graph_before_insert(
    client,
    user_factory,
    active_project_config,
    project_permissions,
    monkeypatch,
):
    from apps.projects import services

    manager = user_factory("lock-path-manager", "Project Manager")
    project = create_project("Lock Path Project", manager)
    ProjectTask = project_task_model()
    first = ProjectTask.objects.create(project=project, title="First pass")
    second = ProjectTask.objects.create(project=project, title="Second pass")
    lock_calls = []
    original_lock = services._lock_project_dependency_graph

    def lock_spy(project_id):
        lock_calls.append(project_id)
        return original_lock(project_id)

    monkeypatch.setattr(services, "_lock_project_dependency_graph", lock_spy)
    client.force_login(manager)

    response = post_json(
        client,
        f"/api/project-tasks/{second.pk}/dependencies/",
        {"depends_on": first.pk},
    )

    assert response.status_code == 201
    assert lock_calls == [project.pk]

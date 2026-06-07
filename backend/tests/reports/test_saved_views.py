from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from apps.accounts.models import ObjectPermission
from apps.audit.models import AuditEvent
from apps.documents.models import Document
from apps.projects.models import Project, ProjectTask
from apps.records.models import Record
from apps.relationships.models import Relationship
from apps.workflows.models import WorkflowDefinition, WorkflowInstance, WorkflowTask


@pytest.fixture
def user_factory(db):
    User = get_user_model()

    def create_user(username, role_name=None, *, is_superuser=False):
        user = User.objects.create_user(
            username=username,
            password="test-pass",
            is_superuser=is_superuser,
        )
        if role_name:
            group, _created = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)
        return user

    return create_user


@pytest.fixture
def report_permissions(db):
    ObjectPermission.objects.create(
        role_name="Product Viewer",
        object_type_key="product",
        can_view=True,
    )
    ObjectPermission.objects.create(
        role_name="Project Viewer",
        object_type_key="project",
        can_view=True,
    )


def post_json(client, path, payload):
    return client.post(path, payload, content_type="application/json")


def create_record(code, object_type_key, title, *, status=Record.Status.DRAFT, data=None, actor=None):
    return Record.objects.create(
        object_type_key=object_type_key,
        code=code,
        title=title,
        status=status,
        schema_version=1,
        data=data or {},
        created_by=actor,
        updated_by=actor,
    )


def create_workflow_task(record, *, assignee, state=WorkflowTask.State.OPEN):
    definition, _created = WorkflowDefinition.objects.get_or_create(
        key=f"workflow_{record.code.lower().replace('-', '_')}",
        defaults={
            "name": f"Workflow {record.code}",
            "object_type_key": record.object_type_key,
        },
    )
    instance, _created = WorkflowInstance.objects.get_or_create(
        definition=definition,
        record=record,
        defaults={"state": "review"},
    )
    return WorkflowTask.objects.create(
        key="approval",
        instance=instance,
        title=f"Approve {record.title}",
        assignee_user=assignee,
        state=state,
        related_record=record,
    )


@pytest.mark.django_db
def test_saved_view_results_apply_supported_filters_and_permissions(
    client,
    user_factory,
    report_permissions,
):
    viewer = user_factory("saved-viewer", "Product Viewer")
    visible_match = create_record(
        "PROD-001",
        "product",
        "Clear Film",
        data={
            "commercial_name": "Clear Medical Film",
            "category": "film",
            "reviewed_on": "2026-02-01",
        },
        actor=viewer,
    )
    visible_related = create_record(
        "PROD-002",
        "product",
        "Resin Carrier",
        data={"commercial_name": "Resin Carrier"},
        actor=viewer,
    )
    create_record(
        "PROD-003",
        "product",
        "Old Film",
        data={"commercial_name": "Old Medical Film", "category": "film", "reviewed_on": "2025-12-31"},
        actor=viewer,
    )
    create_record(
        "MAT-001",
        "raw_material",
        "Hidden Resin",
        data={"commercial_name": "Clear Medical Film", "category": "film", "reviewed_on": "2026-02-01"},
        actor=viewer,
    )
    Relationship.objects.create(
        source_record=visible_match,
        target_record=visible_related,
        relationship_type_key="uses",
    )
    create_workflow_task(visible_match, assignee=viewer)

    client.force_login(viewer)
    create_response = post_json(
        client,
        "/api/saved-views/",
        {
            "name": "Assigned film review",
            "filters": [
                {"type": "object_type", "value": "product"},
                {"type": "status", "value": Record.Status.DRAFT},
                {"type": "field_equals", "field": "category", "value": "film"},
                {"type": "field_contains", "field": "commercial_name", "value": "medical"},
                {"type": "date_after", "field": "reviewed_on", "value": "2026-01-01"},
                {"type": "relationship_exists", "direction": "outgoing", "relationship_type": "uses"},
                {"type": "assigned_workflow_task", "assignee": "me", "state": WorkflowTask.State.OPEN},
            ],
            "columns": ["code", "title", "status"],
        },
    )

    assert create_response.status_code == 201
    saved_view_id = create_response.json()["id"]
    list_response = client.get("/api/saved-views/")
    results_response = client.get(f"/api/saved-views/{saved_view_id}/results/")

    assert list_response.status_code == 200
    assert [item["name"] for item in list_response.json()["results"]] == ["Assigned film review"]
    assert results_response.status_code == 200
    assert [record["id"] for record in results_response.json()["results"]] == [str(visible_match.pk)]
    assert results_response.json()["results"][0]["code"] == "PROD-001"


@pytest.mark.django_db
def test_relationship_exists_respects_direction_related_type_and_endpoint_visibility(
    client,
    user_factory,
    report_permissions,
):
    viewer = user_factory("relationship-viewer", "Product Viewer")
    match = create_record("PROD-REL-1", "product", "Visible outgoing")
    wrong_side = create_record("PROD-REL-2", "product", "Wrong side only")
    hidden_endpoint = create_record("PROD-REL-3", "product", "Hidden endpoint only")
    visible_related = create_record("PROD-REL-4", "product", "Visible related")
    hidden_related = create_record("MAT-REL-1", "raw_material", "Hidden material")
    Relationship.objects.create(
        source_record=match,
        target_record=visible_related,
        relationship_type_key="uses",
    )
    Relationship.objects.create(
        source_record=hidden_related,
        target_record=wrong_side,
        relationship_type_key="uses",
    )
    Relationship.objects.create(
        source_record=hidden_endpoint,
        target_record=hidden_related,
        relationship_type_key="uses",
    )

    client.force_login(viewer)
    create_response = post_json(
        client,
        "/api/saved-views/",
        {
            "name": "Visible related products",
            "filters": [
                {"type": "object_type", "value": "product"},
                {
                    "type": "relationship_exists",
                    "direction": "either",
                    "relationship_type": "uses",
                    "related_object_type_key": "product",
                },
            ],
            "columns": ["code"],
            "sort": ["code"],
        },
    )

    assert create_response.status_code == 201
    results_response = client.get(f"/api/saved-views/{create_response.json()['id']}/results/")

    assert results_response.status_code == 200
    assert [record["code"] for record in results_response.json()["results"]] == [
        "PROD-REL-1",
        "PROD-REL-4",
    ]


@pytest.mark.django_db
def test_relationship_exists_outgoing_and_incoming_hide_unviewable_endpoints(
    client,
    user_factory,
    report_permissions,
):
    viewer = user_factory("relationship-direction-viewer", "Product Viewer")
    outgoing_visible = create_record("PROD-OUT-1", "product", "Outgoing visible")
    incoming_visible = create_record("PROD-IN-1", "product", "Incoming visible")
    visible_related = create_record("PROD-REL-5", "product", "Visible related")
    outgoing_hidden = create_record("PROD-OUT-2", "product", "Outgoing hidden")
    incoming_hidden = create_record("PROD-IN-2", "product", "Incoming hidden")
    hidden_related = create_record("MAT-REL-2", "raw_material", "Hidden material")
    Relationship.objects.create(
        source_record=outgoing_visible,
        target_record=visible_related,
        relationship_type_key="uses",
    )
    Relationship.objects.create(
        source_record=visible_related,
        target_record=incoming_visible,
        relationship_type_key="uses",
    )
    Relationship.objects.create(
        source_record=outgoing_hidden,
        target_record=hidden_related,
        relationship_type_key="uses",
    )
    Relationship.objects.create(
        source_record=hidden_related,
        target_record=incoming_hidden,
        relationship_type_key="uses",
    )

    client.force_login(viewer)
    outgoing_response = post_json(
        client,
        "/api/saved-views/",
        {
            "name": "Outgoing visible",
            "filters": [
                {"type": "object_type", "value": "product"},
                {
                    "type": "relationship_exists",
                    "direction": "outgoing",
                    "relationship_type": "uses",
                },
            ],
            "columns": ["code"],
            "sort": ["code"],
        },
    )
    incoming_response = post_json(
        client,
        "/api/saved-views/",
        {
            "name": "Incoming visible",
            "filters": [
                {"type": "object_type", "value": "product"},
                {
                    "type": "relationship_exists",
                    "direction": "incoming",
                    "relationship_type": "uses",
                },
            ],
            "columns": ["code"],
            "sort": ["code"],
        },
    )

    outgoing_results = client.get(f"/api/saved-views/{outgoing_response.json()['id']}/results/")
    incoming_results = client.get(f"/api/saved-views/{incoming_response.json()['id']}/results/")

    assert outgoing_response.status_code == 201
    assert incoming_response.status_code == 201
    assert [record["code"] for record in outgoing_results.json()["results"]] == [
        "PROD-OUT-1",
        "PROD-REL-5",
    ]
    assert [record["code"] for record in incoming_results.json()["results"]] == [
        "PROD-IN-1",
        "PROD-REL-5",
    ]


@pytest.mark.django_db
def test_saved_view_rejects_unsafe_filter_field_and_malformed_assignee_user(
    client,
    user_factory,
):
    user = user_factory("bad-filter-user")
    client.force_login(user)

    unsafe_response = post_json(
        client,
        "/api/saved-views/",
        {
            "name": "Unsafe field",
            "filters": [{"type": "field_contains", "field": "x__isnull", "value": "bad"}],
        },
    )
    bad_assignee_response = post_json(
        client,
        "/api/saved-views/",
        {
            "name": "Bad assignee",
            "filters": [{"type": "assigned_workflow_task", "assignee_user": "not-a-number"}],
        },
    )

    assert unsafe_response.status_code == 400
    assert "field" in str(unsafe_response.json()["filters"])
    assert bad_assignee_response.status_code == 400
    assert "assignee_user" in str(bad_assignee_response.json()["filters"])


@pytest.mark.django_db
def test_saved_view_results_returns_400_for_invalid_persisted_filter(client, user_factory):
    user = user_factory("persisted-bad-filter-user")
    try:
        from apps.reports.models import SavedView
    except ModuleNotFoundError:
        pytest.fail("reports models are missing")
    saved_view = SavedView.objects.create(
        name="Persisted bad filter",
        owner=user,
        filters=[{"type": "field_contains", "field": "x__isnull", "value": "bad"}],
    )

    client.force_login(user)
    response = client.get(f"/api/saved-views/{saved_view.pk}/results/")

    assert response.status_code == 400
    assert "field" in str(response.json()["filters"])


@pytest.mark.django_db
def test_saved_view_list_is_limited_to_owner(client, user_factory):
    first_user = user_factory("first-owner")
    second_user = user_factory("second-owner")
    try:
        from apps.reports.models import SavedView
    except ModuleNotFoundError:
        pytest.fail("reports models are missing")

    SavedView.objects.create(name="Mine", owner=first_user, filters=[])
    SavedView.objects.create(name="Not mine", owner=second_user, filters=[])

    client.force_login(first_user)
    response = client.get("/api/saved-views/")

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["results"]] == ["Mine"]


@pytest.mark.django_db
def test_private_dashboard_visibility_is_limited_to_owner_and_admin(client, user_factory):
    owner = user_factory("dashboard-owner")
    other_user = user_factory("dashboard-other")
    admin = user_factory("dashboard-admin", is_superuser=True)
    try:
        from apps.reports.models import Dashboard
    except ModuleNotFoundError:
        pytest.fail("reports models are missing")

    private_dashboard = Dashboard.objects.create(name="Private", owner=owner, config={"secret": "owner-only"})
    global_dashboard = Dashboard.objects.create(name="Global")

    client.force_login(other_user)
    private_response = client.get(f"/api/dashboards/{private_dashboard.pk}/")
    global_response = client.get(f"/api/dashboards/{global_dashboard.pk}/")
    client.force_login(admin)
    admin_response = client.get(f"/api/dashboards/{private_dashboard.pk}/")

    assert private_response.status_code == 404
    assert global_response.status_code == 200
    assert global_response.json()["name"] == "Global"
    assert admin_response.status_code == 200
    assert admin_response.json()["config"] == {"secret": "owner-only"}


@pytest.mark.django_db
def test_dashboard_detail_handles_malformed_widget_config(client, user_factory):
    user = user_factory("malformed-widget-viewer")
    try:
        from apps.reports.models import Dashboard, DashboardWidget
    except ModuleNotFoundError:
        pytest.fail("reports models are missing")

    dashboard = Dashboard.objects.create(name="Malformed Widget Config")
    DashboardWidget.objects.create(
        dashboard=dashboard,
        title="Malformed count",
        widget_type="count_by_status",
        config=["not", "a", "dict"],
    )

    client.force_login(user)
    response = client.get(f"/api/dashboards/{dashboard.pk}/")

    assert response.status_code == 200
    assert response.json()["widgets"][0]["data"] == {"items": []}


@pytest.mark.django_db
def test_dashboard_record_widgets_are_permission_filtered(client, user_factory, report_permissions):
    viewer = user_factory("dashboard-viewer", "Product Viewer")
    product = create_record("PROD-DASH", "product", "Dashboard Product", status=Record.Status.RELEASED)
    create_record("MAT-DASH", "raw_material", "Hidden Material", status=Record.Status.DRAFT)
    Document.objects.create(
        title="Safety Data Sheet",
        owner_record=product,
        document_type="sds",
    )
    AuditEvent.objects.create(
        actor=viewer,
        action="record.updated",
        object_type="record",
        object_id=str(product.pk),
        after={"object_type_key": "product"},
    )
    try:
        from apps.reports.models import Dashboard, DashboardWidget
    except ModuleNotFoundError:
        pytest.fail("reports models are missing")

    dashboard = Dashboard.objects.create(name="Quality")
    DashboardWidget.objects.create(
        dashboard=dashboard,
        title="By status",
        widget_type="count_by_status",
        sort_order=1,
    )
    DashboardWidget.objects.create(
        dashboard=dashboard,
        title="By type",
        widget_type="count_by_object_type",
        sort_order=2,
    )
    DashboardWidget.objects.create(
        dashboard=dashboard,
        title="Missing docs",
        widget_type="missing_required_documents",
        config={"requirements": [{"object_type_key": "product", "document_types": ["sds", "tds"]}]},
        sort_order=3,
    )
    DashboardWidget.objects.create(
        dashboard=dashboard,
        title="Recent changes",
        widget_type="recent_changes",
        config={"limit": 5},
        sort_order=4,
    )

    client.force_login(viewer)
    response = client.get(f"/api/dashboards/{dashboard.pk}/")

    assert response.status_code == 200
    widgets = {widget["title"]: widget["data"] for widget in response.json()["widgets"]}
    assert widgets["By status"]["items"] == [{"key": Record.Status.RELEASED, "count": 1}]
    assert widgets["By type"]["items"] == [{"key": "product", "count": 1}]
    assert widgets["Missing docs"]["items"] == [
        {
            "record_id": str(product.pk),
            "code": "PROD-DASH",
            "title": "Dashboard Product",
            "object_type_key": "product",
            "missing_document_types": ["tds"],
        }
    ]
    assert [item["action"] for item in widgets["Recent changes"]["items"]] == ["record.updated"]


@pytest.mark.django_db
def test_dashboard_task_widgets_are_permission_filtered(client, user_factory, report_permissions):
    viewer = user_factory("task-dashboard-viewer", "Project Viewer")
    visible_project_record = create_record("PRJ-001", "project", "Visible Project")
    hidden_project_record = create_record("PRJ-002", "hidden_project", "Hidden Project")
    visible_project = Project.objects.create(record=visible_project_record, name="Visible Project")
    hidden_project = Project.objects.create(record=hidden_project_record, name="Hidden Project")
    overdue = ProjectTask.objects.create(
        project=visible_project,
        title="Overdue visible task",
        due_date=date.today() - timedelta(days=1),
        state=ProjectTask.State.IN_PROGRESS,
    )
    ProjectTask.objects.create(
        project=hidden_project,
        title="Hidden overdue task",
        due_date=date.today() - timedelta(days=1),
        state=ProjectTask.State.IN_PROGRESS,
    )
    workflow_record = create_record("PROD-BOT", "project", "Workflow Bottleneck")
    old_task = create_workflow_task(workflow_record, assignee=viewer)
    WorkflowTask.objects.filter(pk=old_task.pk).update(created_at=timezone.now() - timedelta(days=10))
    old_task.refresh_from_db()
    done_task = create_workflow_task(workflow_record, assignee=viewer, state=WorkflowTask.State.DONE)
    try:
        from apps.reports.models import Dashboard, DashboardWidget
    except ModuleNotFoundError:
        pytest.fail("reports models are missing")

    dashboard = Dashboard.objects.create(name="Tasks")
    DashboardWidget.objects.create(
        dashboard=dashboard,
        title="Overdue tasks",
        widget_type="overdue_project_tasks",
        config={"limit": 10},
        sort_order=1,
    )
    DashboardWidget.objects.create(
        dashboard=dashboard,
        title="Bottlenecks",
        widget_type="workflow_bottlenecks",
        config={"limit": 10},
        sort_order=2,
    )

    client.force_login(viewer)
    response = client.get(f"/api/dashboards/{dashboard.pk}/")

    assert response.status_code == 200
    widgets = {widget["title"]: widget["data"] for widget in response.json()["widgets"]}
    assert widgets["Overdue tasks"]["items"] == [
        {
            "id": overdue.pk,
            "title": "Overdue visible task",
            "project_id": str(visible_project.pk),
            "project_name": "Visible Project",
            "due_date": str(date.today() - timedelta(days=1)),
            "state": ProjectTask.State.IN_PROGRESS,
        }
    ]
    assert widgets["Bottlenecks"]["items"] == [
        {
            "key": "approval",
            "title": "Approve Workflow Bottleneck",
            "state": WorkflowTask.State.OPEN,
            "count": 1,
            "oldest_task_created_at": old_task.created_at.isoformat().replace("+00:00", "Z"),
        }
    ]
    assert done_task.state == WorkflowTask.State.DONE

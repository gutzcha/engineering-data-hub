# ===
# File Summary
# Path: backend\tests\workflows\test_engine.py
# Type: python
# Purpose: Backend test suite validating domain invariants and API behavior.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: user_factory, create_user, release_workflow, test_product_release_requires_fields_and_completed_approval_task, test_workflow_routes_create_complete_and_release_approval_task
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

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.models import ObjectPermission
from apps.documents.models import Document
from apps.records.models import Record
from apps.workflows.engine import WorkflowGuardError, get_or_create_instance_for_record, perform_transition
from apps.workflows.models import (
    WorkflowDefinition,
    WorkflowEvent,
    WorkflowInstance,
    WorkflowTask,
    WorkflowTransition,
)


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
def release_workflow(db):
    definition = WorkflowDefinition.objects.create(
        key="product_release",
        name="Product Release",
        object_type_key="product",
        initial_state="draft",
    )
    WorkflowTransition.objects.create(
        definition=definition,
        key="request_approval",
        label="Request Approval",
        from_state="draft",
        to_state="pending_approval",
        guards={"required_fields": ["commercial_name", "markets"]},
        task_templates=[
            {
                "key": "release_approval",
                "title": "Approve product release",
                "description": "Review the product before release.",
                "assignee_role": "Approver",
                "required": True,
            }
        ],
    )
    WorkflowTransition.objects.create(
        definition=definition,
        key="release",
        label="Release",
        from_state="pending_approval",
        to_state="released",
        guards={
            "required_permission": "release",
            "required_tasks_complete": ["release_approval"],
        },
    )
    return definition


@pytest.mark.django_db
def test_product_release_requires_fields_and_completed_approval_task(
    user_factory,
    release_workflow,
):
    engineer = user_factory("workflow-engineer", "Engineer")
    approver = user_factory("workflow-approver", "Approver")
    ObjectPermission.objects.create(
        role_name="Approver",
        object_type_key="product",
        can_view=True,
        can_release=True,
    )
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-WF-001",
        title="Draft Product",
        schema_version=1,
        data={},
        created_by=engineer,
        updated_by=engineer,
    )
    instance = WorkflowInstance.objects.create(
        definition=release_workflow,
        record=record,
        state="draft",
        created_by=engineer,
        updated_by=engineer,
    )

    with pytest.raises(WorkflowGuardError) as missing_fields:
        perform_transition(str(instance.pk), "request_approval", engineer.pk)

    assert "commercial_name" in str(missing_fields.value)
    instance.refresh_from_db()
    assert instance.state == "draft"
    assert WorkflowTask.objects.count() == 0

    record.data = {"commercial_name": "Clear Film", "markets": ["medical"]}
    record.save(update_fields=["data", "updated_at"])
    instance = perform_transition(str(instance.pk), "request_approval", engineer.pk, "Ready")

    assert instance.state == "pending_approval"
    approval_task = WorkflowTask.objects.get(instance=instance)
    assert approval_task.key == "release_approval"
    assert approval_task.assignee_role == "Approver"
    assert approval_task.state == WorkflowTask.State.OPEN

    with pytest.raises(WorkflowGuardError) as open_task:
        perform_transition(str(instance.pk), "release", approver.pk)

    assert "release_approval" in str(open_task.value)
    approval_task.mark_done(approver)
    instance = perform_transition(str(instance.pk), "release", approver.pk)

    assert instance.state == "released"
    assert WorkflowEvent.objects.filter(
        instance=instance,
        action="transition_performed",
        actor=approver,
        data__transition_key="release",
    ).exists()


@pytest.mark.django_db
def test_workflow_routes_create_complete_and_release_approval_task(
    client,
    user_factory,
    release_workflow,
):
    engineer = user_factory("api-workflow-engineer", "Engineer")
    approver = user_factory("api-workflow-approver", "Approver")
    ObjectPermission.objects.create(
        role_name="Engineer",
        object_type_key="product",
        can_view=True,
        can_edit=True,
    )
    ObjectPermission.objects.create(
        role_name="Approver",
        object_type_key="product",
        can_view=True,
        can_release=True,
    )
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-WF-API",
        title="API Product",
        schema_version=1,
        data={"commercial_name": "API Film", "markets": ["medical"]},
        created_by=engineer,
        updated_by=engineer,
    )

    client.force_login(engineer)
    workflow_response = client.get(f"/api/records/{record.pk}/workflow/")
    request_response = client.post(
        f"/api/records/{record.pk}/workflow/request_approval/",
        {"comment": "Ready for API approval"},
        content_type="application/json",
    )

    assert workflow_response.status_code == 200
    assert workflow_response.json()["state"] == "draft"
    assert request_response.status_code == 200
    assert request_response.json()["state"] == "pending_approval"

    client.force_login(approver)
    tasks_response = client.get("/api/workflow-tasks/?state=open")

    assert tasks_response.status_code == 200
    tasks = tasks_response.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Approve product release"

    complete_response = client.post(
        f"/api/workflow-tasks/{tasks[0]['id']}/complete/",
        {"comment": "Approved"},
        content_type="application/json",
    )
    release_response = client.post(
        f"/api/records/{record.pk}/workflow/release/",
        {},
        content_type="application/json",
    )

    assert complete_response.status_code == 200
    assert complete_response.json()["state"] == WorkflowTask.State.DONE
    assert release_response.status_code == 200
    assert release_response.json()["state"] == "released"


@pytest.mark.django_db
def test_workflow_task_list_post_creates_operator_task_for_record(
    client,
    user_factory,
    release_workflow,
):
    engineer = user_factory("api-task-creator", "Engineer")
    ObjectPermission.objects.create(
        role_name="Engineer",
        object_type_key="product",
        can_view=True,
        can_edit=True,
    )
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-WF-TASK",
        title="Task Product",
        schema_version=1,
        data={"commercial_name": "Task Film", "markets": ["medical"]},
        created_by=engineer,
        updated_by=engineer,
    )
    client.force_login(engineer)

    response = client.post(
        "/api/workflow-tasks/",
        {
            "title": "Investigate supplier issue",
            "description": "Created from Task Inbox",
            "related_record": str(record.pk),
            "assignee_user": engineer.pk,
            "due_date": "2026-07-01T09:00:00Z",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Investigate supplier issue"
    assert body["related_record"] == str(record.pk)
    assert body["assignee_user"] == engineer.pk
    task = WorkflowTask.objects.get(pk=body["id"])
    assert task.instance.record == record
    assert task.created_by == engineer
    assert WorkflowEvent.objects.filter(task=task, action="task_created", actor=engineer).exists()


@pytest.mark.django_db
def test_transition_guards_require_actor_role_and_document_type(user_factory):
    engineer = user_factory("workflow-document-engineer", "Engineer")
    reviewer = user_factory("workflow-reviewer", "Reviewer")
    definition = WorkflowDefinition.objects.create(
        key="technical_review",
        name="Technical Review",
        object_type_key="product",
        initial_state="draft",
    )
    WorkflowTransition.objects.create(
        definition=definition,
        key="review",
        label="Review",
        from_state="draft",
        to_state="reviewed",
        guards={
            "required_role": "Reviewer",
            "required_document_types": ["technical_data_sheet"],
        },
    )
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-WF-DOC",
        title="Document Guard Product",
        schema_version=1,
        data={"commercial_name": "Documented Film"},
        created_by=engineer,
        updated_by=engineer,
    )
    instance = WorkflowInstance.objects.create(
        definition=definition,
        record=record,
        state="draft",
        created_by=engineer,
        updated_by=engineer,
    )

    with pytest.raises(WorkflowGuardError) as missing_guards:
        perform_transition(str(instance.pk), "review", engineer.pk)

    assert "Reviewer" in str(missing_guards.value)
    assert "technical_data_sheet" in str(missing_guards.value)

    Document.objects.create(
        title="Technical Data Sheet",
        owner_record=record,
        document_type="technical_data_sheet",
    )
    updated_instance = perform_transition(str(instance.pk), "review", reviewer.pk)

    assert updated_instance.state == "reviewed"


@pytest.mark.django_db
def test_complete_cancelled_workflow_task_is_rejected_without_completion_event(
    client,
    user_factory,
    release_workflow,
):
    approver = user_factory("cancelled-task-approver", "Approver")
    ObjectPermission.objects.create(
        role_name="Approver",
        object_type_key="product",
        can_view=True,
        can_release=True,
    )
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-WF-CANCELLED",
        title="Cancelled Task Product",
        schema_version=1,
        data={"commercial_name": "Cancelled Task Film", "markets": ["medical"]},
        created_by=approver,
        updated_by=approver,
    )
    instance = WorkflowInstance.objects.create(
        definition=release_workflow,
        record=record,
        state="pending_approval",
        created_by=approver,
        updated_by=approver,
    )
    task = WorkflowTask.objects.create(
        key="release_approval",
        instance=instance,
        title="Approve product release",
        assignee_role="Approver",
        related_record=record,
        state=WorkflowTask.State.CANCELLED,
    )

    client.force_login(approver)
    response = client.post(
        f"/api/workflow-tasks/{task.pk}/complete/",
        {"comment": "Cannot approve this"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "cancelled" in response.json()["detail"].lower()
    task.refresh_from_db()
    assert task.state == WorkflowTask.State.CANCELLED
    assert task.completed_by is None
    assert WorkflowEvent.objects.filter(task=task, action="task_completed").count() == 0


@pytest.mark.django_db
def test_stale_done_workflow_task_object_does_not_duplicate_completion_event(
    user_factory,
    release_workflow,
):
    approver = user_factory("done-task-approver", "Approver")
    ObjectPermission.objects.create(
        role_name="Approver",
        object_type_key="product",
        can_view=True,
        can_release=True,
    )
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-WF-DONE",
        title="Done Task Product",
        schema_version=1,
        data={"commercial_name": "Done Task Film", "markets": ["medical"]},
        created_by=approver,
        updated_by=approver,
    )
    instance = WorkflowInstance.objects.create(
        definition=release_workflow,
        record=record,
        state="pending_approval",
        created_by=approver,
        updated_by=approver,
    )
    task = WorkflowTask.objects.create(
        key="release_approval",
        instance=instance,
        title="Approve product release",
        assignee_role="Approver",
        related_record=record,
    )
    stale_task = WorkflowTask.objects.get(pk=task.pk)
    task.mark_done(approver, "Initial approval")
    completed_at = task.completed_at

    stale_task.mark_done(approver, "Second approval")

    task.refresh_from_db()
    assert task.state == WorkflowTask.State.DONE
    assert task.completed_at == completed_at
    assert WorkflowEvent.objects.filter(task=task, action="task_completed").count() == 1


@pytest.mark.django_db
def test_record_workflow_returns_existing_inactive_definition_instance_before_creating_new_one(
    client,
    user_factory,
    release_workflow,
):
    engineer = user_factory("existing-instance-engineer", "Engineer")
    ObjectPermission.objects.create(
        role_name="Engineer",
        object_type_key="product",
        can_view=True,
        can_edit=True,
    )
    old_definition = release_workflow
    old_definition.is_active = False
    old_definition.save(update_fields=["is_active", "updated_at"])
    new_definition = WorkflowDefinition.objects.create(
        key="product_release_v2",
        name="Product Release V2",
        object_type_key="product",
        initial_state="draft",
        version=2,
        is_active=True,
    )
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-WF-EXISTING",
        title="Existing Workflow Product",
        schema_version=1,
        data={"commercial_name": "Existing Film", "markets": ["medical"]},
        created_by=engineer,
        updated_by=engineer,
    )
    old_instance = WorkflowInstance.objects.create(
        definition=old_definition,
        record=record,
        state="pending_approval",
        created_by=engineer,
        updated_by=engineer,
    )
    WorkflowTransition.objects.create(
        definition=new_definition,
        key="noop",
        label="Noop",
        from_state="draft",
        to_state="draft",
    )

    instance = get_or_create_instance_for_record(record, engineer)

    assert instance == old_instance
    assert WorkflowInstance.objects.filter(record=record).count() == 1

    client.force_login(engineer)
    response = client.get(f"/api/records/{record.pk}/workflow/")

    assert response.status_code == 200
    assert response.json()["id"] == str(old_instance.pk)
    assert response.json()["definition"] == old_definition.key
    assert WorkflowInstance.objects.filter(record=record).count() == 1


import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.config_registry.seed import starter_configuration_data
from apps.config_registry.services import create_draft_from_current, publish_draft, validate_draft
from apps.documents.models import Document
from apps.records.models import Record
from apps.records.validation import validate_record_data
from apps.reports.models import Dashboard, DashboardWidget
from apps.workflows.engine import (
    WorkflowGuardError,
    get_or_create_instance_for_record,
    perform_transition,
)
from apps.workflows.models import WorkflowDefinition, WorkflowTask, WorkflowTransition


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "config_registry"
    / "fixtures"
    / "plastic_engineering_v1.json"
)


EXPECTED_OBJECT_FIELDS = {
    "product": {
        "commercial_name",
        "internal_grade",
        "resin_family",
        "application",
        "color",
        "regulatory_notes",
        "status_notes",
    },
    "raw_material": {
        "supplier_material_code",
        "material_family",
        "supplier",
        "melt_flow_index",
        "density",
        "color",
        "technical_data_sheet",
        "compliance_documents",
    },
    "product_spec": {
        "spec_number",
        "product",
        "revision",
        "effective_date",
        "controlled_document",
        "release_notes",
    },
    "supplier": {
        "supplier_name",
        "supplier_code",
        "contact_email",
        "approved_status",
    },
    "customer": {
        "customer_name",
        "customer_code",
        "market_segment",
    },
    "project": {
        "project_name",
        "project_type",
        "target_launch_date",
        "project_owner",
        "linked_product",
    },
}


def _by_key(items):
    return {item["key"]: item for item in items}


def _field_keys(object_type):
    return {field["key"] for field in object_type["fields"]}


def _field_by_key(object_type, field_key):
    return next(field for field in object_type["fields"] if field["key"] == field_key)


def test_starter_configuration_loads_from_plastic_engineering_fixture():
    assert FIXTURE_PATH.exists()

    fixture_data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert starter_configuration_data() == fixture_data


def test_starter_configuration_contains_required_plastic_engineering_content():
    data = starter_configuration_data()
    object_types = _by_key(data["object_types"])

    assert set(EXPECTED_OBJECT_FIELDS).issubset(object_types)
    for object_type_key, expected_fields in EXPECTED_OBJECT_FIELDS.items():
        assert _field_keys(object_types[object_type_key]) == expected_fields

    assert {"test_method", "document"}.issubset(object_types)

    workflow_keys = {workflow["key"] for workflow in data["workflows"]}
    assert {
        "engineering_record_release",
        "product_spec_release",
        "raw_material_approval",
        "project_gate_review",
    }.issubset(workflow_keys)

    folder_templates = _by_key(data["folder_templates"])
    assert {
        "product_standard",
        "raw_material_standard",
        "project_standard",
        "supplier_standard",
    }.issubset(folder_templates)
    assert folder_templates["product_standard"]["pattern"] == "Products/{code}_{title}"
    assert folder_templates["raw_material_standard"]["pattern"] == "Raw_Materials/{code}_{title}"
    assert folder_templates["project_standard"]["pattern"] == "Projects/{code}_{title}"
    assert folder_templates["supplier_standard"]["pattern"] == "Suppliers/{code}_{title}"

    dashboards = _by_key(data["dashboards"])
    assert {
        "engineering_overview",
        "document_health",
        "project_workload",
        "missing_data",
    }.issubset(dashboards)
    assert all(dashboard["widgets"] for dashboard in dashboards.values())

    widget_types = {
        widget["type"]
        for dashboard in dashboards.values()
        for widget in dashboard["widgets"]
    }
    assert {
        "count_by_status",
        "count_by_object_type",
        "overdue_project_tasks",
        "missing_required_documents",
        "recent_changes",
        "workflow_bottlenecks",
    }.issubset(widget_types)


@pytest.mark.django_db
def test_starter_record_refs_use_runtime_target_key_and_validate_target_type():
    User = get_user_model()
    user = User.objects.create_user(username="starter-ref-admin", password="test-pass")
    draft = create_draft_from_current(user)
    publish_draft(draft, user)
    object_types = _by_key(starter_configuration_data()["object_types"])

    record_ref_fields = [
        _field_by_key(object_types["raw_material"], "supplier"),
        _field_by_key(object_types["product_spec"], "product"),
        _field_by_key(object_types["project"], "linked_product"),
    ]
    assert all(field.get("target_object_type") for field in record_ref_fields)
    assert all("reference_target_type" not in field for field in record_ref_fields)

    supplier = Record.objects.create(
        object_type_key="supplier",
        code="SUP-REF-001",
        title="Supplier Ref",
        schema_version=1,
        data={},
    )
    product = Record.objects.create(
        object_type_key="product",
        code="PROD-REF-001",
        title="Product Ref",
        schema_version=1,
        data={},
    )

    with pytest.raises(serializers.ValidationError) as raw_material_error:
        validate_record_data(
            "raw_material",
            {
                "supplier_material_code": "RM-BAD",
                "material_family": "Base Resin",
                "supplier": str(product.pk),
            },
        )
    assert raw_material_error.value.detail["data"]["supplier"][0] == (
        "Referenced record must be a supplier."
    )
    validate_record_data(
        "raw_material",
        {
            "supplier_material_code": "RM-GOOD",
            "material_family": "Base Resin",
            "supplier": str(supplier.pk),
        },
    )

    with pytest.raises(serializers.ValidationError) as spec_error:
        validate_record_data(
            "product_spec",
            {
                "spec_number": "SPEC-BAD",
                "product": str(supplier.pk),
                "revision": "A",
            },
        )
    assert spec_error.value.detail["data"]["product"][0] == (
        "Referenced record must be a product."
    )

    with pytest.raises(serializers.ValidationError) as project_error:
        validate_record_data(
            "project",
            {
                "project_name": "Bad Linked Product",
                "project_type": "New Product",
                "linked_product": str(supplier.pk),
            },
        )
    assert project_error.value.detail["data"]["linked_product"][0] == (
        "Referenced record must be a product."
    )


@pytest.mark.django_db
def test_starter_configuration_publishes_cleanly():
    User = get_user_model()
    user = User.objects.create_user(username="starter-config-admin", password="test-pass")
    draft = create_draft_from_current(user)

    assert validate_draft(draft) == []

    version = publish_draft(draft, user)

    assert version.version == 1
    assert version.data == starter_configuration_data()


@pytest.mark.django_db
def test_publish_syncs_starter_workflows_and_dashboards_to_runtime_models(client):
    User = get_user_model()
    user = User.objects.create_superuser(
        username="starter-runtime-admin",
        password="test-pass",
    )
    draft = create_draft_from_current(user)

    publish_draft(draft, user)

    workflow = WorkflowDefinition.objects.get(
        key="engineering_record_release__product",
        object_type_key="product",
    )
    assert workflow.name == "Engineering Record Release"
    assert workflow.initial_state == "draft"
    assert workflow.version == 1
    assert workflow.data["config_registry_managed"] is True
    assert list(workflow.transitions.values_list("key", flat=True)) == [
        "draft_to_engineering_review",
        "engineering_review_to_quality_review",
        "quality_review_to_released",
    ]
    product = Record.objects.create(
        object_type_key="product",
        code="PROD-WF-STARTER",
        title="Starter Workflow Product",
        schema_version=1,
        data={"commercial_name": "Starter Workflow Product"},
    )
    instance = get_or_create_instance_for_record(product, user)
    assert instance.definition == workflow

    dashboard = Dashboard.objects.get(config__key="engineering_overview", owner__isnull=True)
    assert dashboard.config["config_registry_managed"] is True
    assert list(dashboard.widgets.values_list("widget_type", flat=True)) == [
        "count_by_status",
        "count_by_object_type",
        "recent_changes",
    ]
    client.force_login(user)
    response = client.get("/api/dashboards/engineering_overview/")
    assert response.status_code == 200
    assert [widget["widget_type"] for widget in response.json()["widgets"]] == [
        "count_by_status",
        "count_by_object_type",
        "recent_changes",
    ]

    second_draft = create_draft_from_current(user)
    second_draft.data["workflows"][0]["label"] = "Engineering Record Release Updated"
    second_draft.data["dashboards"][0]["widgets"][0]["title"] = "Updated Records by Status"
    second_draft.save()
    publish_draft(second_draft, user)

    workflow.refresh_from_db()
    dashboard.refresh_from_db()
    assert workflow.name == "Engineering Record Release Updated"
    assert WorkflowDefinition.objects.filter(key="engineering_record_release__product").count() == 1
    assert WorkflowTransition.objects.filter(definition=workflow).count() == 3
    assert Dashboard.objects.filter(config__key="engineering_overview").count() == 1
    assert DashboardWidget.objects.get(
        dashboard=dashboard,
        widget_type="count_by_status",
        sort_order=0,
    ).title == "Updated Records by Status"


@pytest.mark.django_db
def test_bootstrapped_starter_workflow_enforces_guards_and_task_roles():
    User = get_user_model()
    user = User.objects.create_superuser(
        username="starter-guard-admin",
        password="test-pass",
    )
    draft = create_draft_from_current(user)
    publish_draft(draft, user)
    product = Record.objects.create(
        object_type_key="product",
        code="PROD-WF-GUARD",
        title="Guard Product",
        schema_version=1,
        data={"commercial_name": "Guard Product"},
    )
    spec = Record.objects.create(
        object_type_key="product_spec",
        code="SPEC-WF-GUARD",
        title="Guard Spec",
        schema_version=1,
        data={"spec_number": "SPEC-WF-GUARD", "product": str(product.pk)},
    )
    instance = get_or_create_instance_for_record(spec, user)

    with pytest.raises(WorkflowGuardError) as missing_revision:
        perform_transition(str(instance.pk), "draft_to_technical_review", user.pk)

    assert "revision" in str(missing_revision.value)
    spec.data["revision"] = "A"
    spec.save(update_fields=["data", "updated_at"])
    instance = perform_transition(str(instance.pk), "draft_to_technical_review", user.pk)
    technical_task = WorkflowTask.objects.get(instance=instance, key="technical_spec_review")
    assert technical_task.assignee_role == "Engineering Reviewer"

    with pytest.raises(WorkflowGuardError) as missing_task_and_document:
        perform_transition(str(instance.pk), "technical_review_to_approval", user.pk)

    assert "technical_spec_review" in str(missing_task_and_document.value)
    assert "controlled_document" in str(missing_task_and_document.value)

    technical_task.mark_done(user)
    Document.objects.create(
        title="Controlled Spec",
        owner_record=spec,
        document_type="controlled_document",
    )
    instance = perform_transition(str(instance.pk), "technical_review_to_approval", user.pk)
    approval_task = WorkflowTask.objects.get(instance=instance, key="approver_signoff")
    assert approval_task.assignee_role == "Quality Reviewer"

    with pytest.raises(WorkflowGuardError) as missing_approval_task:
        perform_transition(str(instance.pk), "approval_to_released", user.pk)

    assert "approver_signoff" in str(missing_approval_task.value)
    approval_task.mark_done(user)
    instance = perform_transition(str(instance.pk), "approval_to_released", user.pk)
    assert instance.state == "released"


@pytest.mark.django_db
def test_publish_retires_removed_config_managed_runtime_rows():
    User = get_user_model()
    user = User.objects.create_superuser(
        username="starter-stale-admin",
        password="test-pass",
    )
    draft = create_draft_from_current(user)
    publish_draft(draft, user)
    stale_workflow = WorkflowDefinition.objects.get(key="raw_material_approval__raw_material")
    assert stale_workflow.is_active is True
    assert Dashboard.objects.filter(config__key="document_health").exists()
    unmanaged_workflow = WorkflowDefinition.objects.create(
        key="unmanaged_quality_review",
        name="Unmanaged Quality Review",
        object_type_key="product",
        initial_state="draft",
        data={},
    )
    unmanaged_dashboard = Dashboard.objects.create(
        name="Unmanaged Dashboard",
        config={"key": "unmanaged_dashboard"},
    )

    second_draft = create_draft_from_current(user)
    second_draft.data["workflows"] = [
        workflow
        for workflow in second_draft.data["workflows"]
        if workflow["key"] != "raw_material_approval"
    ]
    second_draft.data["dashboards"] = [
        dashboard
        for dashboard in second_draft.data["dashboards"]
        if dashboard["key"] != "document_health"
    ]
    second_draft.save()
    publish_draft(second_draft, user)

    stale_workflow.refresh_from_db()
    unmanaged_workflow.refresh_from_db()
    unmanaged_dashboard.refresh_from_db()
    assert stale_workflow.is_active is False
    assert not Dashboard.objects.filter(
        config__key="document_health",
        config__config_registry_managed=True,
    ).exists()
    assert unmanaged_workflow.is_active is True
    assert Dashboard.objects.filter(pk=unmanaged_dashboard.pk).exists()


@pytest.mark.django_db
def test_multi_object_workflow_keys_remain_stable_when_first_assignment_is_removed():
    User = get_user_model()
    user = User.objects.create_superuser(
        username="starter-multi-workflow-admin",
        password="test-pass",
    )
    draft = create_draft_from_current(user)
    publish_draft(draft, user)
    product_definition = WorkflowDefinition.objects.get(
        key="engineering_record_release__product",
        object_type_key="product",
    )
    test_method_definition = WorkflowDefinition.objects.get(
        key="engineering_record_release__test_method",
        object_type_key="test_method",
    )
    document_definition = WorkflowDefinition.objects.get(
        key="engineering_record_release__document",
        object_type_key="document",
    )
    unmanaged_workflow = WorkflowDefinition.objects.create(
        key="unmanaged_starter_release",
        name="Unmanaged Starter Release",
        object_type_key="product",
        initial_state="draft",
        data={},
    )

    second_draft = create_draft_from_current(user)
    product_type = next(
        object_type
        for object_type in second_draft.data["object_types"]
        if object_type["key"] == "product"
    )
    product_type.pop("default_workflow_key")
    second_draft.save()
    publish_draft(second_draft, user)

    product_definition.refresh_from_db()
    test_method_definition.refresh_from_db()
    document_definition.refresh_from_db()
    unmanaged_workflow.refresh_from_db()
    assert product_definition.is_active is False
    assert product_definition.object_type_key == "product"
    assert test_method_definition.is_active is True
    assert test_method_definition.object_type_key == "test_method"
    assert document_definition.is_active is True
    assert document_definition.object_type_key == "document"
    assert WorkflowDefinition.objects.filter(
        key="engineering_record_release__test_method",
    ).count() == 1
    assert WorkflowDefinition.objects.filter(
        key="engineering_record_release",
        data__config_registry_managed=True,
    ).count() == 0
    assert unmanaged_workflow.is_active is True

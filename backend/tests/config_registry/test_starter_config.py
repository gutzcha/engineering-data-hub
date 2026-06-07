import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model

from apps.config_registry.seed import starter_configuration_data
from apps.config_registry.services import create_draft_from_current, publish_draft, validate_draft


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
def test_starter_configuration_publishes_cleanly():
    User = get_user_model()
    user = User.objects.create_user(username="starter-config-admin", password="test-pass")
    draft = create_draft_from_current(user)

    assert validate_draft(draft) == []

    version = publish_draft(draft, user)

    assert version.version == 1
    assert version.data == starter_configuration_data()

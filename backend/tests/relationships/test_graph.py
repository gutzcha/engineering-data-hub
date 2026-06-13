# ===
# File Summary
# Path: backend\tests\relationships\test_graph.py
# Type: python
# Purpose: Backend test suite validating domain invariants and API behavior.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: user_factory, create_user, active_config, relationship_permissions, graph_records
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
from apps.config_registry.services import create_draft_from_current, publish_draft
from apps.records.models import Record
from apps.relationships.models import Relationship


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
def active_config(user_factory):
    user = user_factory("relationship-config-publisher")
    draft = create_draft_from_current(user)
    draft.data = {
        "object_types": [
            _object_type("product", "Product", "PROD", "commercial_name"),
            _object_type("raw_material", "Raw Material", "RM", "material_name"),
            _object_type("product_spec", "Product Spec", "SPEC", "spec_name"),
            _object_type("supplier", "Supplier", "SUP", "supplier_name"),
            _object_type("project", "Project", "PRJ", "project_name"),
        ],
        "relationship_types": [
            {
                "key": "product_uses_material",
                "label": "Product uses material",
                "source_object_type": "product",
                "target_object_type": "raw_material",
            },
            {
                "key": "product_has_spec",
                "label": "Product has spec",
                "source_object_type": "product",
                "target_object_type": "product_spec",
            },
            {
                "key": "project_affects_product",
                "label": "Project affects product",
                "source_object_type": "project",
                "target_object_type": "product",
            },
            {
                "key": "supplier_provides_material",
                "label": "Supplier provides material",
                "source_object_type": "supplier",
                "target_object_type": "raw_material",
            },
            {
                "key": "product_has_supplier",
                "label": "Product has supplier",
                "source_object_type": "product",
                "target_object_type": "supplier",
            },
        ],
        "form_layouts": [],
        "folder_templates": [],
        "dashboards": [],
    }
    draft.save()
    return publish_draft(draft, user)


@pytest.fixture
def relationship_permissions(db):
    for object_type_key in ["product", "raw_material", "product_spec", "supplier", "project"]:
        ObjectPermission.objects.create(
            role_name="Graph Engineer",
            object_type_key=object_type_key,
            can_view=True,
            can_create=True,
            can_edit=True,
        )
        ObjectPermission.objects.create(
            role_name="Graph Viewer",
            object_type_key=object_type_key,
            can_view=True,
        )


@pytest.fixture
def graph_records(active_config):
    return {
        "product": _record(active_config, "product", "PROD-000001", "Clear Film"),
        "material": _record(active_config, "raw_material", "RM-000001", "Resin A"),
        "spec": _record(active_config, "product_spec", "SPEC-000001", "Film Spec"),
        "supplier": _record(active_config, "supplier", "SUP-000001", "Resin Supplier"),
        "project": _record(active_config, "project", "PRJ-000001", "Cost Down"),
    }


def post_json(client, path, payload):
    return client.post(path, payload, content_type="application/json")


def _object_type(key, label, code_prefix, title_field):
    return {
        "key": key,
        "label": label,
        "plural_label": f"{label}s",
        "code_pattern": f"{code_prefix}-{{seq:000000}}",
        "title_field": title_field,
        "fields": [{"key": title_field, "label": label, "type": "text", "required": True}],
    }


def _record(active_config, object_type_key, code, title):
    return Record.objects.create(
        object_type_key=object_type_key,
        code=code,
        title=title,
        schema_version=active_config.version,
        data={},
    )


def _create_relationship(client, source, target, relationship_type_key, data=None):
    return post_json(
        client,
        "/api/relationships/",
        {
            "source_record": str(source.pk),
            "target_record": str(target.pk),
            "relationship_type_key": relationship_type_key,
            "data": data or {},
        },
    )


@pytest.mark.django_db
def test_graph_returns_product_material_spec_project_and_supplier_edges(
    client,
    user_factory,
    active_config,
    relationship_permissions,
    graph_records,
):
    client.force_login(user_factory("graph-engineer", "Graph Engineer"))
    relationships = [
        _create_relationship(
            client,
            graph_records["product"],
            graph_records["material"],
            "product_uses_material",
        ),
        _create_relationship(
            client,
            graph_records["product"],
            graph_records["spec"],
            "product_has_spec",
        ),
        _create_relationship(
            client,
            graph_records["project"],
            graph_records["product"],
            "project_affects_product",
        ),
        _create_relationship(
            client,
            graph_records["supplier"],
            graph_records["material"],
            "supplier_provides_material",
            {"qualification": "approved"},
        ),
    ]
    assert [response.status_code for response in relationships] == [201, 201, 201, 201]

    response = client.get(f"/api/records/{graph_records['product'].pk}/graph/")

    assert response.status_code == 200
    body = response.json()
    assert {
        (node["object_type_key"], node["code"], node["label"]) for node in body["nodes"]
    } == {
        ("product", "PROD-000001", "Clear Film"),
        ("raw_material", "RM-000001", "Resin A"),
        ("product_spec", "SPEC-000001", "Film Spec"),
        ("supplier", "SUP-000001", "Resin Supplier"),
        ("project", "PRJ-000001", "Cost Down"),
    }
    assert {
        (
            edge["source"],
            edge["target"],
            edge["relationship_type_key"],
            edge["label"],
        )
        for edge in body["edges"]
    } == {
        (
            str(graph_records["product"].pk),
            str(graph_records["material"].pk),
            "product_uses_material",
            "Product uses material",
        ),
        (
            str(graph_records["product"].pk),
            str(graph_records["spec"].pk),
            "product_has_spec",
            "Product has spec",
        ),
        (
            str(graph_records["project"].pk),
            str(graph_records["product"].pk),
            "project_affects_product",
            "Project affects product",
        ),
        (
            str(graph_records["supplier"].pk),
            str(graph_records["material"].pk),
            "supplier_provides_material",
            "Supplier provides material",
        ),
    }
    supplier_edge = next(
        edge
        for edge in body["edges"]
        if edge["relationship_type_key"] == "supplier_provides_material"
    )
    assert supplier_edge["data"] == {"qualification": "approved"}


@pytest.mark.django_db
def test_create_rejects_unknown_relationship_type(
    client,
    user_factory,
    active_config,
    relationship_permissions,
    graph_records,
):
    client.force_login(user_factory("unknown-type-engineer", "Graph Engineer"))

    response = _create_relationship(
        client,
        graph_records["product"],
        graph_records["material"],
        "product_has_distributor",
    )

    assert response.status_code == 400
    assert response.json()["relationship_type_key"][0] == "Unknown relationship type."


@pytest.mark.django_db
def test_create_rejects_source_and_target_that_do_not_match_relationship_type(
    client,
    user_factory,
    active_config,
    relationship_permissions,
    graph_records,
):
    client.force_login(user_factory("mismatch-engineer", "Graph Engineer"))

    response = _create_relationship(
        client,
        graph_records["material"],
        graph_records["product"],
        "product_uses_material",
    )

    assert response.status_code == 400
    assert response.json()["source_record"][0] == "Source record must be a product."
    assert response.json()["target_record"][0] == "Target record must be a raw_material."


@pytest.mark.django_db
def test_create_and_delete_relationship_require_edit_permission_on_source(
    client,
    user_factory,
    active_config,
    relationship_permissions,
    graph_records,
):
    client.force_login(user_factory("relationship-viewer", "Graph Viewer"))
    denied_create = _create_relationship(
        client,
        graph_records["product"],
        graph_records["material"],
        "product_uses_material",
    )
    assert denied_create.status_code == 403

    client.force_login(user_factory("relationship-engineer", "Graph Engineer"))
    created = _create_relationship(
        client,
        graph_records["product"],
        graph_records["material"],
        "product_uses_material",
    )
    assert created.status_code == 201

    client.force_login(user_factory("relationship-delete-viewer", "Graph Viewer"))
    denied_delete = client.delete(f"/api/relationships/{created.json()['id']}/")
    assert denied_delete.status_code == 403

    client.force_login(user_factory("relationship-delete-engineer", "Graph Engineer"))
    deleted = client.delete(f"/api/relationships/{created.json()['id']}/")
    assert deleted.status_code == 204


@pytest.mark.django_db
def test_relationship_create_and_delete_enqueue_related_record_indexing(
    client,
    user_factory,
    active_config,
    relationship_permissions,
    graph_records,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    from apps.search import tasks

    indexed_record_ids = []
    monkeypatch.setattr(tasks.index_record, "delay", lambda record_id: indexed_record_ids.append(record_id))
    client.force_login(user_factory("relationship-index-engineer", "Graph Engineer"))

    with django_capture_on_commit_callbacks(execute=True):
        created = _create_relationship(
            client,
            graph_records["product"],
            graph_records["material"],
            "product_uses_material",
        )
        assert created.status_code == 201
        deleted = client.delete(f"/api/relationships/{created.json()['id']}/")
        assert deleted.status_code == 204

    expected = [
        str(graph_records["product"].pk),
        str(graph_records["material"].pk),
        str(graph_records["product"].pk),
        str(graph_records["material"].pk),
    ]
    assert indexed_record_ids == expected


@pytest.mark.django_db
def test_graph_requires_view_permission_on_root_record(
    client,
    user_factory,
    active_config,
    graph_records,
):
    client.force_login(user_factory("no-graph-permission"))

    response = client.get(f"/api/records/{graph_records['product'].pk}/graph/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_graph_hides_nodes_and_edges_the_user_cannot_view(
    client,
    user_factory,
    active_config,
    relationship_permissions,
    graph_records,
):
    client.force_login(user_factory("relationship-builder", "Graph Engineer"))
    material_relationship = _create_relationship(
        client,
        graph_records["product"],
        graph_records["material"],
        "product_uses_material",
    )
    supplier_relationship = _create_relationship(
        client,
        graph_records["product"],
        graph_records["supplier"],
        "product_has_supplier",
    )
    assert material_relationship.status_code == 201
    assert supplier_relationship.status_code == 201

    ObjectPermission.objects.create(
        role_name="Material Viewer",
        object_type_key="product",
        can_view=True,
    )
    ObjectPermission.objects.create(
        role_name="Material Viewer",
        object_type_key="raw_material",
        can_view=True,
    )

    client.force_login(user_factory("material-viewer", "Material Viewer"))
    response = client.get(f"/api/records/{graph_records['product'].pk}/graph/")

    assert response.status_code == 200
    body = response.json()
    assert {node["object_type_key"] for node in body["nodes"]} == {
        "product",
        "raw_material",
    }
    assert {
        (edge["source"], edge["target"], edge["relationship_type_key"])
        for edge in body["edges"]
    } == {
        (
            str(graph_records["product"].pk),
            str(graph_records["material"].pk),
            "product_uses_material",
        )
    }


@pytest.mark.django_db
def test_create_checks_permissions_before_relationship_type_compatibility(
    client,
    user_factory,
    active_config,
    graph_records,
):
    ObjectPermission.objects.create(
        role_name="Product Editor",
        object_type_key="product",
        can_view=True,
        can_edit=True,
    )
    ObjectPermission.objects.create(
        role_name="Product Editor",
        object_type_key="raw_material",
        can_view=True,
    )
    client.force_login(user_factory("product-editor", "Product Editor"))

    response = _create_relationship(
        client,
        graph_records["product"],
        graph_records["supplier"],
        "product_uses_material",
    )

    assert response.status_code == 403
    response_text = response.content.decode()
    assert "Target record must be a raw_material" not in response_text
    assert "supplier" not in response_text


@pytest.mark.django_db
def test_create_rejects_relationship_when_active_config_has_no_relationship_types(
    client,
    user_factory,
    active_config,
    relationship_permissions,
):
    publisher = user_factory("relationship-config-remover")
    draft = create_draft_from_current(publisher)
    draft.data.pop("relationship_types")
    draft.save()
    config_without_relationship_types = publish_draft(draft, publisher)
    product = _record(
        config_without_relationship_types,
        "product",
        "PROD-000002",
        "Clear Film",
    )
    material = _record(
        config_without_relationship_types,
        "raw_material",
        "RM-000002",
        "Resin A",
    )

    client.force_login(user_factory("no-relationship-types-engineer", "Graph Engineer"))
    response = _create_relationship(
        client,
        product,
        material,
        "product_uses_material",
    )

    assert response.status_code == 400
    assert response.json()["relationship_type_key"][0] == "Unknown relationship type."
    assert not Relationship.objects.exists()


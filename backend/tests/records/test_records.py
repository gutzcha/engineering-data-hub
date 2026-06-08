import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.models import ObjectPermission, RecordPermission
from apps.config_registry.services import create_draft_from_current, publish_draft
from apps.documents.models import Document, DocumentRevision
from apps.records.models import Record


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
    user = user_factory("config-publisher")
    draft = create_draft_from_current(user)
    draft.data = {
        "object_types": [
            {
                "key": "product",
                "label": "Product",
                "plural_label": "Products",
                "code_pattern": "PROD-{seq:000000}",
                "title_field": "commercial_name",
                "fields": [
                    {
                        "key": "commercial_name",
                        "label": "Commercial Name",
                        "type": "text",
                        "required": True,
                        "unique": True,
                    },
                    {
                        "key": "category",
                        "label": "Category",
                        "type": "choice",
                        "options": ["film", "resin"],
                    },
                    {"key": "grade", "label": "Grade", "type": "number"},
                    {"key": "active", "label": "Active", "type": "boolean"},
                    {
                        "key": "markets",
                        "label": "Markets",
                        "type": "multi_choice",
                        "required": True,
                        "options": ["medical", "industrial"],
                    },
                    {
                        "key": "source_material",
                        "label": "Source Material",
                        "type": "record_ref",
                        "target_object_type": "raw_material",
                    },
                ],
            },
            {
                "key": "raw_material",
                "label": "Raw Material",
                "plural_label": "Raw Materials",
                "code_pattern": "MAT-{year}-{seq:0000}",
                "title_field": "material_name",
                "fields": [
                    {
                        "key": "material_name",
                        "label": "Material Name",
                        "type": "text",
                        "required": True,
                    },
                    {
                        "key": "form",
                        "label": "Form",
                        "type": "choice",
                        "options": [{"value": "pellet"}, {"value": "powder"}],
                    },
                ],
            },
            {
                "key": "empty_record",
                "label": "Empty Record",
                "plural_label": "Empty Records",
                "code_pattern": "EMPTY-{seq:000000}",
                "fields": [],
            },
        ],
        "form_layouts": [],
        "folder_templates": [],
        "dashboards": [],
    }
    draft.save()
    return publish_draft(draft, user)


@pytest.fixture
def permissions(db):
    ObjectPermission.objects.create(role_name="Viewer", object_type_key="product")
    ObjectPermission.objects.create(role_name="Viewer", object_type_key="raw_material")
    ObjectPermission.objects.create(
        role_name="Engineer",
        object_type_key="product",
        can_view=True,
        can_create=True,
        can_edit=True,
    )
    ObjectPermission.objects.create(
        role_name="Engineer",
        object_type_key="raw_material",
        can_view=True,
        can_create=True,
        can_edit=True,
    )
    ObjectPermission.objects.create(
        role_name="Engineer",
        object_type_key="empty_record",
        can_view=True,
        can_create=True,
        can_edit=True,
    )
    ObjectPermission.objects.create(
        role_name="Approver",
        object_type_key="product",
        can_view=True,
        can_release=True,
    )
    ObjectPermission.objects.create(
        role_name="Product Admin",
        object_type_key="product",
        can_view=True,
        can_create=True,
        can_edit=True,
        can_admin=True,
    )


def post_json(client, path, payload):
    return client.post(path, payload, content_type="application/json")


def patch_json(client, path, payload):
    return client.patch(path, payload, content_type="application/json")


@pytest.mark.django_db
def test_record_detail_includes_owned_document_summaries(
    client,
    user_factory,
    active_config,
    permissions,
):
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-900001",
        title="Documented Product",
        schema_version=active_config.version,
        data={
            "commercial_name": "Documented Product",
            "markets": ["medical"],
        },
    )
    document = Document.objects.create(
        owner_record=record,
        title="Release Specification",
        document_type="specification",
    )
    revision = DocumentRevision.objects.create(
        document=document,
        revision_label="A",
        file_name="release-spec.pdf",
        storage_path="documents/1/revisions/1/release-spec.pdf",
        sha256="abc123",
        size=123,
        mime_type="application/pdf",
        extraction_status="complete",
    )
    document.current_revision = revision
    document.save(update_fields=["current_revision", "updated_at"])
    client.force_login(user_factory("document-summary-viewer", "Viewer"))

    response = client.get(f"/api/records/{record.pk}/")

    assert response.status_code == 200
    body = response.json()
    assert body["documents"] == [
        {
            "id": document.pk,
            "title": "Release Specification",
            "owner_record": str(record.pk),
            "document_type": "specification",
            "current_revision": {
                "id": revision.pk,
                "revision_label": "A",
                "file_name": "release-spec.pdf",
                "sha256": "abc123",
                "size": 123,
                "mime_type": "application/pdf",
                "extraction_status": "complete",
                "state": "draft",
                "created_by": None,
                "released_at": None,
                "created_at": body["documents"][0]["current_revision"]["created_at"],
                "updated_at": body["documents"][0]["current_revision"]["updated_at"],
            },
            "state": "draft",
            "folder": None,
            "created_at": body["documents"][0]["created_at"],
            "updated_at": body["documents"][0]["updated_at"],
        }
    ]


@pytest.mark.django_db
def test_create_record_generates_code_and_title_from_active_config(
    client,
    user_factory,
    active_config,
    permissions,
):
    client.force_login(user_factory("create-engineer", "Engineer"))

    response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {
                "commercial_name": "Clear Film",
                "category": "film",
                "grade": 12.5,
                "markets": ["medical"],
            },
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["object_type_key"] == "product"
    assert body["code"] == "PROD-000001"
    assert body["title"] == "Clear Film"
    assert body["status"] == "draft"
    assert body["schema_version"] == active_config.version
    assert body["created_by"] == body["updated_by"]


@pytest.mark.django_db
def test_create_without_data_defaults_to_empty_object(client, user_factory, active_config, permissions):
    client.force_login(user_factory("empty-record-engineer", "Engineer"))

    response = post_json(client, "/api/records/", {"object_type_key": "empty_record"})

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "EMPTY-000001"
    assert body["title"] == "EMPTY-000001"
    assert body["data"] == {}


@pytest.mark.django_db
def test_create_creates_object_type_lock_row(client, user_factory, active_config, permissions):
    from apps.records.models import RecordObjectTypeLock

    client.force_login(user_factory("lock-row-engineer", "Engineer"))

    response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Locked Product", "markets": ["medical"]},
        },
    )

    assert response.status_code == 201
    assert RecordObjectTypeLock.objects.filter(object_type_key="product").exists() is True


@pytest.mark.django_db
def test_required_field_validation_fails(client, user_factory, active_config, permissions):
    client.force_login(user_factory("required-engineer", "Engineer"))

    response = post_json(client, "/api/records/", {"object_type_key": "product", "data": {}})

    assert response.status_code == 400
    assert response.json()["data"]["commercial_name"][0] == "This field is required."


@pytest.mark.django_db
def test_type_validation_fails(client, user_factory, active_config, permissions):
    client.force_login(user_factory("type-engineer", "Engineer"))

    response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Bad Grade", "grade": True, "markets": ["medical"]},
        },
    )

    assert response.status_code == 400
    assert response.json()["data"]["grade"][0] == "Expected a number."


@pytest.mark.django_db
def test_choice_validation_fails(client, user_factory, active_config, permissions):
    client.force_login(user_factory("choice-engineer", "Engineer"))

    response = post_json(
        client,
        "/api/records/",
        {"object_type_key": "raw_material", "data": {"material_name": "Resin A", "form": "liquid"}},
    )

    assert response.status_code == 400
    assert response.json()["data"]["form"][0] == "Value must be one of: pellet, powder."


@pytest.mark.django_db
def test_required_multi_choice_validation_fails_for_empty_list(
    client,
    user_factory,
    active_config,
    permissions,
):
    client.force_login(user_factory("multi-choice-engineer", "Engineer"))

    response = post_json(
        client,
        "/api/records/",
        {"object_type_key": "product", "data": {"commercial_name": "No Markets", "markets": []}},
    )

    assert response.status_code == 400
    assert response.json()["data"]["markets"][0] == "This field is required."


@pytest.mark.django_db
def test_unique_field_validation_fails(client, user_factory, active_config, permissions):
    client.force_login(user_factory("unique-engineer", "Engineer"))
    payload = {
        "object_type_key": "product",
        "data": {"commercial_name": "Unique Film", "markets": ["medical"]},
    }
    assert post_json(client, "/api/records/", payload).status_code == 201

    response = post_json(client, "/api/records/", payload)

    assert response.status_code == 400
    assert response.json()["data"]["commercial_name"][0] == "Value must be unique within product."


@pytest.mark.django_db
def test_record_ref_target_object_type_validation_fails_and_passes(
    client,
    user_factory,
    active_config,
    permissions,
):
    client.force_login(user_factory("ref-engineer", "Engineer"))
    product_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Reference Product", "markets": ["medical"]},
        },
    )
    material_response = post_json(
        client,
        "/api/records/",
        {"object_type_key": "raw_material", "data": {"material_name": "Reference Resin"}},
    )

    bad_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {
                "commercial_name": "Bad Reference",
                "markets": ["medical"],
                "source_material": product_response.json()["id"],
            },
        },
    )
    good_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {
                "commercial_name": "Good Reference",
                "markets": ["industrial"],
                "source_material": material_response.json()["id"],
            },
        },
    )

    assert bad_response.status_code == 400
    assert bad_response.json()["data"]["source_material"][0] == (
        "Referenced record must be a raw_material."
    )
    assert good_response.status_code == 201


@pytest.mark.django_db
def test_permissions_block_unauthorized_create_edit_and_release(
    client,
    user_factory,
    active_config,
    permissions,
):
    viewer = user_factory("record-viewer", "Viewer")
    engineer = user_factory("record-engineer", "Engineer")
    client.force_login(viewer)

    create_response = post_json(
        client,
        "/api/records/",
        {"object_type_key": "product", "data": {"commercial_name": "No Create", "markets": ["medical"]}},
    )
    assert create_response.status_code == 403

    client.force_login(engineer)
    record_response = post_json(
        client,
        "/api/records/",
        {"object_type_key": "product", "data": {"commercial_name": "Editable", "markets": ["medical"]}},
    )
    record_id = record_response.json()["id"]

    client.force_login(viewer)
    edit_response = patch_json(
        client,
        f"/api/records/{record_id}/",
        {"data": {"commercial_name": "Blocked Edit"}},
    )
    release_response = post_json(client, f"/api/records/{record_id}/release/", {})

    assert edit_response.status_code == 403
    assert release_response.status_code == 403


@pytest.mark.django_db
def test_retrieve_requires_view_permission(client, user_factory, active_config, permissions):
    client.force_login(user_factory("view-owner-engineer", "Engineer"))
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Private Product", "markets": ["medical"]},
        },
    )
    record_id = record_response.json()["id"]

    client.force_login(user_factory("no-record-role"))
    response = client.get(f"/api/records/{record_id}/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_record_list_includes_only_record_scoped_grants(
    client,
    user_factory,
    active_config,
):
    scoped_user = user_factory("record-list-scoped", "Scoped Record Viewer")
    allowed = Record.objects.create(
        object_type_key="product",
        code="PROD-900101",
        title="Visible Scoped Product",
        schema_version=active_config.version,
        data={"commercial_name": "Visible Scoped Product", "markets": ["medical"]},
    )
    denied = Record.objects.create(
        object_type_key="product",
        code="PROD-900102",
        title="Hidden Scoped Product",
        schema_version=active_config.version,
        data={"commercial_name": "Hidden Scoped Product", "markets": ["medical"]},
    )
    RecordPermission.objects.create(
        role_name="Scoped Record Viewer",
        object_type_key="product",
        record=allowed,
        can_view=True,
    )
    client.force_login(scoped_user)

    response = client.get("/api/records/?object_type_key=product")

    assert response.status_code == 200
    assert [record["id"] for record in response.json()] == [str(allowed.pk)]
    assert str(denied.pk) not in {record["id"] for record in response.json()}


@pytest.mark.django_db
def test_record_list_respects_record_level_denies_for_object_viewer(
    client,
    user_factory,
    active_config,
):
    viewer = user_factory("record-list-deny-viewer", "Deny Product Viewer")
    ObjectPermission.objects.create(
        role_name="Deny Product Viewer",
        object_type_key="product",
        can_view=True,
    )
    visible = Record.objects.create(
        object_type_key="product",
        code="PROD-900201",
        title="Globally Visible Product",
        schema_version=active_config.version,
        data={"commercial_name": "Globally Visible Product", "markets": ["medical"]},
    )
    blocked = Record.objects.create(
        object_type_key="product",
        code="PROD-900202",
        title="Blocked Product",
        schema_version=active_config.version,
        data={"commercial_name": "Blocked Product", "markets": ["medical"]},
    )
    RecordPermission.objects.create(
        role_name="Deny Product Viewer",
        object_type_key="product",
        record=blocked,
        can_view=False,
    )
    client.force_login(viewer)

    response = client.get("/api/records/?object_type_key=product")

    assert response.status_code == 200
    assert [record["id"] for record in response.json()] == [str(visible.pk)]


@pytest.mark.django_db
def test_delete_record_route_is_not_supported_for_viewer(
    client,
    user_factory,
    active_config,
    permissions,
):
    client.force_login(user_factory("delete-owner-engineer", "Engineer"))
    record_response = post_json(
        client,
        "/api/records/",
        {"object_type_key": "product", "data": {"commercial_name": "Keep Me", "markets": ["medical"]}},
    )
    record_id = record_response.json()["id"]

    client.force_login(user_factory("delete-viewer", "Viewer"))
    response = client.delete(f"/api/records/{record_id}/")

    assert response.status_code == 405
    assert Record.objects.filter(pk=record_id).exists() is True


@pytest.mark.django_db
def test_release_endpoint_sets_status_released_when_authorized(
    client,
    user_factory,
    active_config,
    permissions,
):
    client.force_login(user_factory("release-engineer", "Engineer"))
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Release Me", "markets": ["medical"]},
        },
    )
    record_id = record_response.json()["id"]

    client.force_login(user_factory("record-approver", "Approver"))
    response = post_json(client, f"/api/records/{record_id}/release/", {})

    assert response.status_code == 200
    assert response.json()["status"] == "released"


@pytest.mark.django_db
def test_record_create_update_and_release_enqueue_search_indexing(
    client,
    user_factory,
    active_config,
    permissions,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    from apps.search import tasks

    indexed_record_ids = []
    monkeypatch.setattr(tasks.index_record, "delay", lambda record_id: indexed_record_ids.append(record_id))
    client.force_login(user_factory("search-indexing-engineer", "Engineer"))

    with django_capture_on_commit_callbacks(execute=True):
        create_response = post_json(
            client,
            "/api/records/",
            {
                "object_type_key": "product",
                "data": {
                    "commercial_name": "Indexed Film",
                    "markets": ["medical"],
                },
            },
        )
        assert create_response.status_code == 201
        record_id = create_response.json()["id"]

        update_response = patch_json(
            client,
            f"/api/records/{record_id}/",
            {"data": {"commercial_name": "Indexed Film Updated"}},
        )
        assert update_response.status_code == 200

        ObjectPermission.objects.update_or_create(
            role_name="Engineer",
            object_type_key="product",
            defaults={
                "can_view": True,
                "can_create": True,
                "can_edit": True,
                "can_release": True,
            },
        )
        release_response = post_json(client, f"/api/records/{record_id}/release/", {})
        assert release_response.status_code == 200

    assert indexed_record_ids == [record_id, record_id, record_id]


@pytest.mark.django_db
def test_release_revalidates_active_config_and_refreshes_schema_version(
    client,
    user_factory,
    active_config,
    permissions,
):
    publisher = user_factory("release-config-publisher")
    engineer = user_factory("release-schema-engineer", "Engineer")
    approver = user_factory("release-schema-approver", "Approver")
    client.force_login(engineer)
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Schema Release Product", "markets": ["medical"]},
        },
    )
    record_id = record_response.json()["id"]
    draft = create_draft_from_current(publisher)
    draft.data["object_types"][0]["fields"].append(
        {
            "key": "compliance_code",
            "label": "Compliance Code",
            "type": "text",
            "required": True,
        }
    )
    draft.save()
    new_config = publish_draft(draft, publisher, confirm_breaking_changes=True)

    client.force_login(approver)
    failed_release = post_json(client, f"/api/records/{record_id}/release/", {})

    assert failed_release.status_code == 400
    assert failed_release.json()["data"]["compliance_code"][0] == "This field is required."

    client.force_login(engineer)
    update_response = patch_json(
        client,
        f"/api/records/{record_id}/",
        {"data": {"compliance_code": "CMP-001"}},
    )
    assert update_response.status_code == 200

    client.force_login(approver)
    release_response = post_json(client, f"/api/records/{record_id}/release/", {})

    assert release_response.status_code == 200
    assert release_response.json()["status"] == "released"
    assert release_response.json()["schema_version"] == new_config.version


@pytest.mark.django_db
def test_create_rejects_released_status_without_release_endpoint(
    client,
    user_factory,
    active_config,
    permissions,
):
    client.force_login(user_factory("create-released-engineer", "Engineer"))

    response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "status": "released",
            "data": {"commercial_name": "Premature Release", "markets": ["medical"]},
        },
    )

    assert response.status_code == 400
    assert response.json()["status"][0] == "New records must be created as draft."


@pytest.mark.django_db
def test_patch_cannot_bypass_release_permission(client, user_factory, active_config, permissions):
    client.force_login(user_factory("bypass-engineer", "Engineer"))
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Bypass Release", "markets": ["medical"]},
        },
    )
    record_id = record_response.json()["id"]

    response = patch_json(client, f"/api/records/{record_id}/", {"status": "released"})

    assert response.status_code == 400
    assert response.json()["status"][0] == "Use the release endpoint to release records."


@pytest.mark.django_db
def test_patch_rejects_object_type_key_change(client, user_factory, active_config, permissions):
    client.force_login(user_factory("object-type-engineer", "Engineer"))
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Stable Type", "markets": ["medical"]},
        },
    )
    record_id = record_response.json()["id"]

    response = patch_json(client, f"/api/records/{record_id}/", {"object_type_key": "raw_material"})

    assert response.status_code == 400
    assert response.json()["object_type_key"][0] == "Object type cannot be changed."
    assert Record.objects.get(pk=record_id).object_type_key == "product"


@pytest.mark.django_db
def test_manual_code_requires_admin_permission(client, user_factory, active_config, permissions):
    client.force_login(user_factory("manual-code-engineer", "Engineer"))

    response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "code": "MANUAL-001",
            "data": {"commercial_name": "Manual Code", "markets": ["medical"]},
        },
    )

    assert response.status_code == 403
    assert Record.objects.filter(code="MANUAL-001").exists() is False


@pytest.mark.django_db
def test_admin_can_create_record_with_manual_code(client, user_factory, active_config, permissions):
    client.force_login(user_factory("manual-code-admin", "Product Admin"))

    response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "code": "MANUAL-ADMIN-001",
            "data": {"commercial_name": "Admin Manual Code", "markets": ["medical"]},
        },
    )

    assert response.status_code == 201
    assert response.json()["code"] == "MANUAL-ADMIN-001"


@pytest.mark.django_db
def test_patch_rejects_code_change(client, user_factory, active_config, permissions):
    client.force_login(user_factory("patch-code-engineer", "Engineer"))
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Stable Code", "markets": ["medical"]},
        },
    )
    record_id = record_response.json()["id"]
    original_code = record_response.json()["code"]

    response = patch_json(client, f"/api/records/{record_id}/", {"code": "CHANGED-001"})

    assert response.status_code == 400
    assert response.json()["code"][0] == "Code cannot be changed."
    assert Record.objects.get(pk=record_id).code == original_code


@pytest.mark.django_db
def test_update_refreshes_schema_version_to_active_config(
    client,
    user_factory,
    active_config,
    permissions,
):
    publisher = user_factory("second-config-publisher")
    client.force_login(user_factory("schema-engineer", "Engineer"))
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Schema Product", "markets": ["medical"]},
        },
    )
    record_id = record_response.json()["id"]
    draft = create_draft_from_current(publisher)
    draft.data["object_types"][0]["label"] = "Updated Product"
    draft.save()
    new_config = publish_draft(draft, publisher)

    response = patch_json(
        client,
        f"/api/records/{record_id}/",
        {"data": {"category": "film"}},
    )

    assert response.status_code == 200
    assert response.json()["schema_version"] == new_config.version


@pytest.mark.django_db
@pytest.mark.parametrize("bad_data", [[], "bad"])
def test_patch_rejects_non_object_data_and_preserves_record(
    client,
    user_factory,
    active_config,
    permissions,
    bad_data,
):
    client.force_login(user_factory(f"bad-data-engineer-{type(bad_data).__name__}", "Engineer"))
    original_data = {"commercial_name": "Stable Data", "markets": ["medical"]}
    record_response = post_json(
        client,
        "/api/records/",
        {"object_type_key": "product", "data": original_data},
    )
    record_id = record_response.json()["id"]

    response = patch_json(client, f"/api/records/{record_id}/", {"data": bad_data})

    assert response.status_code == 400
    assert response.json()["data"][0] == "Expected an object."
    assert Record.objects.get(pk=record_id).data == original_data


@pytest.mark.django_db
def test_update_revalidates_data_and_refreshes_title(client, user_factory, active_config, permissions):
    client.force_login(user_factory("update-engineer", "Engineer"))
    record_response = post_json(
        client,
        "/api/records/",
        {"object_type_key": "product", "data": {"commercial_name": "Old Name", "markets": ["medical"]}},
    )
    record_id = record_response.json()["id"]

    response = patch_json(
        client,
        f"/api/records/{record_id}/",
        {"data": {"commercial_name": "New Name", "category": "resin"}},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "New Name"
    assert response.json()["data"]["category"] == "resin"

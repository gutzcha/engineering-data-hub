# ===
# File Summary
# Path: backend\tests\folders\test_scanner.py
# Type: python
# Purpose: Backend test suite validating domain invariants and API behavior.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: user_factory, create_user, product_record, generated_folder, test_folder_generation_creates_directories_and_managed_folder
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

from apps.accounts.models import ObjectPermission, RecordPermission
from apps.folders.models import FolderChangeEvent, ManagedFolder
from apps.folders.scanner import scan_managed_folder
from apps.folders.services import generate_managed_folder
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
def product_record(db):
    return Record.objects.create(
        object_type_key="product",
        code="PROD-000010",
        title="Scanner Film",
        schema_version=1,
        data={},
    )


@pytest.fixture
def generated_folder(product_record, settings, tmp_path):
    settings.MANAGED_FILE_ROOT = tmp_path
    return generate_managed_folder(product_record)


@pytest.mark.django_db
def test_folder_generation_creates_directories_and_managed_folder(
    product_record,
    settings,
    tmp_path,
):
    settings.MANAGED_FILE_ROOT = tmp_path

    managed_folder = generate_managed_folder(product_record)

    assert managed_folder.record == product_record
    assert managed_folder.template_key == "product_standard"
    assert managed_folder.state == "active"
    assert (tmp_path / "Products" / "PROD-000010_Scanner_Film").is_dir()
    assert (tmp_path / "Products" / "PROD-000010_Scanner_Film" / "01_Specifications").is_dir()
    assert ManagedFolder.objects.filter(record=product_record, folder_role="primary").count() == 1


@pytest.mark.django_db
def test_folder_generation_is_idempotent_for_existing_managed_folder(
    product_record,
    settings,
    tmp_path,
):
    settings.MANAGED_FILE_ROOT = tmp_path
    first = generate_managed_folder(product_record)

    second = generate_managed_folder(product_record)

    assert second == first
    assert second.relative_path == "Products/PROD-000010_Scanner_Film"
    assert ManagedFolder.objects.filter(record=product_record, folder_role="primary").count() == 1
    assert not FolderChangeEvent.objects.filter(event_type="collision").exists()


@pytest.mark.django_db
def test_direct_added_file_creates_pending_added_event(generated_folder, tmp_path):
    scan_managed_folder(generated_folder)
    target = tmp_path / generated_folder.relative_path / "01_Specifications" / "new-spec.txt"
    target.write_text("first version", encoding="utf-8")

    events = scan_managed_folder(generated_folder)

    assert [event.event_type for event in events] == ["added"]
    event = events[0]
    assert event.path == f"{generated_folder.relative_path}/01_Specifications/new-spec.txt"
    assert event.review_status == "pending"
    assert event.detected_hash


@pytest.mark.django_db
def test_scanner_enqueues_created_folder_events_for_search(
    generated_folder,
    tmp_path,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    from apps.search import tasks

    indexed_event_ids = []
    monkeypatch.setattr(tasks.index_folder_event, "delay", lambda event_id: indexed_event_ids.append(event_id))
    scan_managed_folder(generated_folder)
    target = tmp_path / generated_folder.relative_path / "01_Specifications" / "indexed.txt"
    target.write_text("first version", encoding="utf-8")

    with django_capture_on_commit_callbacks(execute=True):
        events = scan_managed_folder(generated_folder)

    assert indexed_event_ids == [events[0].pk]


@pytest.mark.django_db
def test_file_added_before_first_scan_creates_pending_added_event(generated_folder, tmp_path):
    target = tmp_path / generated_folder.relative_path / "01_Specifications" / "pre-scan.txt"
    target.write_text("created before scanner ever ran", encoding="utf-8")

    events = scan_managed_folder(generated_folder)

    assert [event.event_type for event in events] == ["added"]
    assert events[0].path == f"{generated_folder.relative_path}/01_Specifications/pre-scan.txt"
    assert events[0].review_status == "pending"


@pytest.mark.django_db
def test_modified_file_creates_modified_event(generated_folder, tmp_path):
    target = tmp_path / generated_folder.relative_path / "01_Specifications" / "spec.txt"
    target.write_text("first version", encoding="utf-8")
    scan_managed_folder(generated_folder)
    target.write_text("second version", encoding="utf-8")

    events = scan_managed_folder(generated_folder)

    assert [event.event_type for event in events] == ["modified"]
    assert events[0].path == f"{generated_folder.relative_path}/01_Specifications/spec.txt"


@pytest.mark.django_db
def test_deleted_file_creates_deleted_event(generated_folder, tmp_path):
    target = tmp_path / generated_folder.relative_path / "01_Specifications" / "obsolete.txt"
    target.write_text("first version", encoding="utf-8")
    scan_managed_folder(generated_folder)
    target.unlink()

    events = scan_managed_folder(generated_folder)

    assert [event.event_type for event in events] == ["deleted"]
    assert events[0].path == f"{generated_folder.relative_path}/01_Specifications/obsolete.txt"


@pytest.mark.django_db
def test_moved_file_creates_moved_event(generated_folder, tmp_path):
    source = tmp_path / generated_folder.relative_path / "01_Specifications" / "old-name.txt"
    target = tmp_path / generated_folder.relative_path / "02_Drawings" / "new-name.txt"
    source.write_text("same content", encoding="utf-8")
    scan_managed_folder(generated_folder)
    source.rename(target)

    events = scan_managed_folder(generated_folder)

    assert [event.event_type for event in events] == ["moved"]
    assert events[0].path == (
        f"{generated_folder.relative_path}/01_Specifications/old-name.txt -> "
        f"{generated_folder.relative_path}/02_Drawings/new-name.txt"
    )


@pytest.mark.django_db
def test_review_routes_update_status(client, user_factory, generated_folder):
    event = FolderChangeEvent.objects.create(
        event_type="added",
        path=f"{generated_folder.relative_path}/01_Specifications/review.txt",
        detected_hash="abc",
        matched_record=generated_folder.record,
        managed_folder=generated_folder,
    )
    admin = user_factory("folder-admin", is_superuser=True)
    client.force_login(admin)

    list_response = client.get("/api/folder-events/")
    accept_response = client.post(f"/api/folder-events/{event.pk}/accept/")
    event.refresh_from_db()
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert accept_response.status_code == 200
    assert event.review_status == "accepted"
    assert event.reviewer == admin

    ignored = FolderChangeEvent.objects.create(
        event_type="modified",
        path=f"{generated_folder.relative_path}/01_Specifications/ignore.txt",
        managed_folder=generated_folder,
        matched_record=generated_folder.record,
    )
    ignore_response = client.post(f"/api/folder-events/{ignored.pk}/ignore/")
    ignored.refresh_from_db()

    assert ignore_response.status_code == 200
    assert ignored.review_status == "ignored"


@pytest.mark.django_db
def test_review_route_enqueues_folder_event_search_indexing(
    client,
    user_factory,
    generated_folder,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    from apps.search import tasks

    event = FolderChangeEvent.objects.create(
        event_type="added",
        path=f"{generated_folder.relative_path}/01_Specifications/review-index.txt",
        detected_hash="abc",
        matched_record=generated_folder.record,
        managed_folder=generated_folder,
    )
    indexed_event_ids = []
    monkeypatch.setattr(tasks.index_folder_event, "delay", lambda event_id: indexed_event_ids.append(event_id))
    client.force_login(user_factory("folder-index-admin", is_superuser=True))

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(f"/api/folder-events/{event.pk}/accept/")

    assert response.status_code == 200
    assert indexed_event_ids == [event.pk]


@pytest.mark.django_db
def test_assign_folder_event_updates_assignee_and_audits(client, user_factory, generated_folder):
    from apps.audit.models import AuditEvent

    event = FolderChangeEvent.objects.create(
        event_type="added",
        path=f"{generated_folder.relative_path}/01_Specifications/assign.txt",
        detected_hash="abc",
        matched_record=generated_folder.record,
        managed_folder=generated_folder,
    )
    admin = user_factory("folder-assign-admin", is_superuser=True)
    assignee = user_factory("folder-assignee")
    client.force_login(admin)

    response = client.post(
        f"/api/folder-events/{event.pk}/assign/",
        {"assignee": assignee.pk},
        content_type="application/json",
    )

    event.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["assigned_to"] == assignee.pk
    assert response.json()["assignee_username"] == "folder-assignee"
    assert event.assigned_to == assignee
    audit_event = AuditEvent.objects.get(action="folder_event.assigned")
    assert audit_event.before["assigned_to_id"] is None
    assert audit_event.after["assigned_to_id"] == assignee.pk

    clear_response = client.post(
        f"/api/folder-events/{event.pk}/assign/",
        {"assigned_to": ""},
        content_type="application/json",
    )

    event.refresh_from_db()
    assert clear_response.status_code == 200
    assert clear_response.json()["assigned_to"] is None
    assert event.assigned_to is None


@pytest.mark.django_db
def test_link_document_creates_metadata_document_and_marks_event_linked(
    client,
    user_factory,
    generated_folder,
):
    from apps.audit.models import AuditEvent
    from apps.documents.models import Document

    event = FolderChangeEvent.objects.create(
        event_type="added",
        path=f"{generated_folder.relative_path}/01_Specifications/link.txt",
        managed_folder=generated_folder,
        matched_record=generated_folder.record,
    )
    admin = user_factory("folder-link-admin", is_superuser=True)
    client.force_login(admin)

    response = client.post(f"/api/folder-events/{event.pk}/link-document/")

    assert response.status_code == 201
    body = response.json()
    document = Document.objects.get(pk=body["document"]["id"])
    event.refresh_from_db()
    assert document.title == "link.txt"
    assert document.document_type == "folder_event"
    assert document.owner_record == generated_folder.record
    assert document.folder == generated_folder
    assert document.current_revision is None
    assert event.review_status == "linked"
    assert event.reviewer == admin
    assert body["event"]["review_status"] == "linked"
    audit_event = AuditEvent.objects.get(action="folder_event.document_linked")
    assert audit_event.after["review_status"] == "linked"
    assert audit_event.after["linked_document_id"] == document.pk


@pytest.mark.django_db
def test_review_routes_allow_user_with_edit_permission(client, user_factory, generated_folder):
    ObjectPermission.objects.create(
        role_name="Folder Engineer",
        object_type_key="product",
        can_view=True,
        can_edit=True,
    )
    event = FolderChangeEvent.objects.create(
        event_type="added",
        path=f"{generated_folder.relative_path}/01_Specifications/editable.txt",
        managed_folder=generated_folder,
        matched_record=generated_folder.record,
    )
    client.force_login(user_factory("folder-engineer", "Folder Engineer"))

    response = client.post(f"/api/folder-events/{event.pk}/accept/")

    assert response.status_code == 200
    event.refresh_from_db()
    assert event.review_status == "accepted"


@pytest.mark.django_db
def test_review_inbox_filters_events_by_view_permission(client, user_factory):
    product = Record.objects.create(
        object_type_key="product",
        code="PROD-000011",
        title="Visible Product",
        schema_version=1,
        data={},
    )
    raw_material = Record.objects.create(
        object_type_key="raw_material",
        code="MAT-000011",
        title="Hidden Material",
        schema_version=1,
        data={},
    )
    supplier = Record.objects.create(
        object_type_key="supplier",
        code="SUP-000011",
        title="Hidden Supplier",
        schema_version=1,
        data={},
    )
    visible = FolderChangeEvent.objects.create(
        event_type="added",
        path="Products/PROD-000011_Visible_Product/spec.txt",
        matched_record=product,
    )
    hidden_material = FolderChangeEvent.objects.create(
        event_type="added",
        path="Raw_Materials/MAT-000011_Hidden_Material/tds.txt",
        matched_record=raw_material,
    )
    hidden_supplier = FolderChangeEvent.objects.create(
        event_type="added",
        path="Suppliers/SUP-000011_Hidden_Supplier/cert.txt",
        matched_record=supplier,
    )
    unmatched = FolderChangeEvent.objects.create(
        event_type="collision",
        path="Unmatched/path",
    )
    ObjectPermission.objects.create(
        role_name="Product Viewer",
        object_type_key="product",
        can_view=True,
    )
    client.force_login(user_factory("product-folder-viewer", "Product Viewer"))

    list_response = client.get("/api/folder-events/")
    visible_response = client.get(f"/api/folder-events/{visible.pk}/")
    hidden_response = client.get(f"/api/folder-events/{hidden_material.pk}/")
    supplier_response = client.get(f"/api/folder-events/{hidden_supplier.pk}/")
    unmatched_response = client.get(f"/api/folder-events/{unmatched.pk}/")

    assert list_response.status_code == 200
    assert [event["id"] for event in list_response.json()] == [visible.pk]
    assert visible_response.status_code == 200
    assert hidden_response.status_code == 404
    assert supplier_response.status_code == 404
    assert unmatched_response.status_code == 404


@pytest.mark.django_db
def test_review_inbox_filters_events_by_record_level_permission(client, user_factory):
    first = Record.objects.create(
        object_type_key="product",
        code="PROD-000041",
        title="Visible Folder Product",
        schema_version=1,
        data={},
    )
    second = Record.objects.create(
        object_type_key="product",
        code="PROD-000042",
        title="Hidden Folder Product",
        schema_version=1,
        data={},
    )
    visible = FolderChangeEvent.objects.create(
        event_type="added",
        path="Products/PROD-000041/spec.txt",
        matched_record=first,
    )
    hidden = FolderChangeEvent.objects.create(
        event_type="added",
        path="Products/PROD-000042/spec.txt",
        matched_record=second,
    )
    RecordPermission.objects.create(
        role_name="Scoped Folder Viewer",
        object_type_key="product",
        record=first,
        can_view=True,
    )
    client.force_login(user_factory("scoped-folder-viewer", "Scoped Folder Viewer"))

    list_response = client.get("/api/folder-events/")
    visible_response = client.get(f"/api/folder-events/{visible.pk}/")
    hidden_response = client.get(f"/api/folder-events/{hidden.pk}/")

    assert list_response.status_code == 200
    assert [event["id"] for event in list_response.json()] == [visible.pk]
    assert visible_response.status_code == 200
    assert hidden_response.status_code == 404


@pytest.mark.django_db
def test_folder_event_detail_includes_non_pending_events_for_authorized_viewer(client, user_factory):
    product = Record.objects.create(
        object_type_key="product",
        code="PROD-000031",
        title="Accepted Product",
        schema_version=1,
        data={},
    )
    accepted = FolderChangeEvent.objects.create(
        event_type="added",
        path="Products/PROD-000031/accepted.txt",
        matched_record=product,
        review_status=FolderChangeEvent.ReviewStatus.ACCEPTED,
    )
    ObjectPermission.objects.create(
        role_name="Accepted Folder Viewer",
        object_type_key="product",
        can_view=True,
    )
    client.force_login(user_factory("accepted-folder-viewer", "Accepted Folder Viewer"))

    list_response = client.get("/api/folder-events/")
    detail_response = client.get(f"/api/folder-events/{accepted.pk}/")

    assert list_response.status_code == 200
    assert list_response.json() == []
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == accepted.pk
    assert detail_response.json()["review_status"] == "accepted"


@pytest.mark.django_db
def test_folder_event_list_can_filter_to_one_record(client, user_factory):
    first = Record.objects.create(
        object_type_key="product",
        code="PROD-000021",
        title="First Product",
        schema_version=1,
        data={},
    )
    second = Record.objects.create(
        object_type_key="product",
        code="PROD-000022",
        title="Second Product",
        schema_version=1,
        data={},
    )
    first_event = FolderChangeEvent.objects.create(
        event_type="added",
        path="Products/PROD-000021/spec.txt",
        matched_record=first,
    )
    FolderChangeEvent.objects.create(
        event_type="added",
        path="Products/PROD-000022/spec.txt",
        matched_record=second,
    )
    ObjectPermission.objects.create(
        role_name="Product Folder Viewer",
        object_type_key="product",
        can_view=True,
    )
    client.force_login(user_factory("record-folder-viewer", "Product Folder Viewer"))

    response = client.get(f"/api/folder-events/?record={first.pk}")

    assert response.status_code == 200
    assert [event["id"] for event in response.json()] == [first_event.pk]


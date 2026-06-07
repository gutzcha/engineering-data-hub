from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from openpyxl import Workbook

from apps.accounts.models import ObjectPermission
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.config_registry.services import create_draft_from_current, publish_draft
from apps.folders.models import FolderChangeEvent
from apps.imports.models import ImportJob
from apps.imports.services import dry_run_import


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
    user = user_factory("audit-config-publisher")
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
                    {
                        "key": "markets",
                        "label": "Markets",
                        "type": "multi_choice",
                        "required": True,
                        "options": ["medical", "industrial"],
                    },
                ],
            }
        ],
        "form_layouts": [],
        "folder_templates": [],
        "dashboards": [],
    }
    draft.save()
    return publish_draft(draft, user)


@pytest.fixture
def permissions(db):
    ObjectPermission.objects.create(
        role_name="Engineer",
        object_type_key="product",
        can_view=True,
        can_create=True,
        can_edit=True,
    )
    ObjectPermission.objects.create(
        role_name="Product Admin",
        object_type_key="product",
        can_view=True,
        can_create=True,
        can_edit=True,
        can_admin=True,
    )


def post_json(client, path, payload, **extra):
    return client.post(path, payload, content_type="application/json", **extra)


def patch_json(client, path, payload):
    return client.patch(path, payload, content_type="application/json")


def workbook_file(rows, name="records.xlsx"):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return ContentFile(output.getvalue(), name=name)


def import_mapping():
    return {
        "columns": {
            "Code": "code",
            "Commercial Name": "commercial_name",
            "Category": "category",
        }
    }


@pytest.mark.django_db
def test_updating_product_field_records_old_and_new_values(
    client,
    user_factory,
    active_config,
    permissions,
):
    user = user_factory("audit-engineer", "Engineer")
    client.force_login(user)
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {
                "commercial_name": "Audit Film",
                "category": "film",
                "markets": ["medical"],
            },
        },
    )
    record_id = record_response.json()["id"]

    response = patch_json(
        client,
        f"/api/records/{record_id}/",
        {"data": {"category": "resin", "grade": 12.5}},
    )

    assert response.status_code == 200
    event = AuditEvent.objects.get(action="record.updated", object_id=record_id)
    assert event.actor == user
    assert event.object_type == "record"
    assert event.before["data"]["category"] == "film"
    assert event.before["data"].get("grade") is None
    assert event.after["data"]["category"] == "resin"
    assert event.after["data"]["grade"] == 12.5
    assert event.request_id
    assert event.ip_address
    assert event.user_agent

    audit_response = client.get(f"/api/records/{record_id}/audit/")

    assert audit_response.status_code == 200
    assert audit_response.json()["results"][0]["id"] == event.id


@pytest.mark.django_db
def test_audit_events_are_append_only_and_api_is_read_only(client, user_factory):
    user = user_factory("audit-row-user")
    event = AuditEvent.objects.create(
        actor=user,
        action="record.updated",
        object_type="record",
        object_id="record-1",
        before={"data": {"category": "film"}},
        after={"data": {"category": "resin"}},
        request_id="req-1",
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    event.action = "tampered"
    with pytest.raises(ValidationError):
        event.save()

    with pytest.raises(ValidationError):
        event.delete()

    client.force_login(user)
    response = patch_json(client, "/api/audit/", {"action": "tampered"})

    assert response.status_code == 405


@pytest.mark.django_db
def test_folder_generation_service_audit_records_request_metadata(
    client,
    user_factory,
    active_config,
    permissions,
    settings,
    tmp_path,
):
    settings.MANAGED_FILE_ROOT = tmp_path
    user = user_factory("audit-folder-admin", "Product Admin")
    client.force_login(user)
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Folder Audit Film", "markets": ["medical"]},
        },
    )
    record_id = record_response.json()["id"]

    response = post_json(
        client,
        f"/api/records/{record_id}/folders/generate/",
        {},
        HTTP_X_REQUEST_ID="folder-request-1",
        HTTP_USER_AGENT="audit-test-agent",
        REMOTE_ADDR="203.0.113.10",
    )

    assert response.status_code == 200
    event = AuditEvent.objects.get(action="folder.generated")
    assert event.request_id == "folder-request-1"
    assert event.user_agent == "audit-test-agent"
    assert event.ip_address == "203.0.113.10"


@pytest.mark.django_db
def test_request_metadata_ignores_spoofed_forwarded_for_and_sanitizes_request_id(
    client,
    user_factory,
    active_config,
    permissions,
):
    user = user_factory("audit-metadata-engineer", "Engineer")
    client.force_login(user)

    response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Metadata Audit Film", "markets": ["medical"]},
        },
        HTTP_X_REQUEST_ID="bad request id !",
        HTTP_X_FORWARDED_FOR="198.51.100.99",
        REMOTE_ADDR="203.0.113.30",
    )

    assert response.status_code == 201
    event = AuditEvent.objects.get(action="record.created", object_id=response.json()["id"])
    assert event.ip_address == "203.0.113.30"
    assert event.request_id != "bad request id !"
    assert len(event.request_id) == 32
    assert all(character in "0123456789abcdef" for character in event.request_id)
    assert response["X-Request-ID"] == event.request_id


@pytest.mark.django_db
def test_audit_persistence_failure_and_non_json_payload_do_not_break_business_path(
    monkeypatch,
    user_factory,
):
    user = user_factory("audit-failure-user")

    record_audit_event(
        user,
        "audit.normalized_probe",
        "target-1",
        before={"bad": {3, 1, 2}},
        after={"user": user},
    )
    event = AuditEvent.objects.get(action="audit.normalized_probe")
    assert event.before["bad"] == [1, 2, 3]
    assert event.after["user"] == str(user.pk)

    def fail_create(**kwargs):
        raise RuntimeError("audit store is unavailable")

    monkeypatch.setattr(AuditEvent.objects, "create", fail_create)

    record_audit_event(
        user,
        "audit.failure_probe",
        "target-1",
        before={"bad": {3, 1, 2}},
        after={"user": user},
    )


@pytest.mark.django_db
def test_failed_audit_db_write_inside_atomic_does_not_rollback_record_update(
    client,
    monkeypatch,
    user_factory,
    active_config,
    permissions,
):
    user = user_factory("audit-db-failure-engineer", "Engineer")
    client.force_login(user)
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {
                "commercial_name": "DB Failure Audit Film",
                "category": "film",
                "markets": ["medical"],
            },
        },
    )
    record_id = record_response.json()["id"]

    def fail_with_real_db_error(**kwargs):
        AuditEvent(action=None, object_type="record", object_id="bad").save(force_insert=True)

    monkeypatch.setattr(AuditEvent.objects, "create", fail_with_real_db_error)

    response = patch_json(
        client,
        f"/api/records/{record_id}/",
        {"data": {"category": "resin"}},
    )

    assert response.status_code == 200
    refreshed_response = client.get(f"/api/records/{record_id}/")
    assert refreshed_response.status_code == 200
    assert refreshed_response.json()["data"]["category"] == "resin"


@pytest.mark.django_db
def test_folder_review_mutation_creates_audit_event(
    client,
    user_factory,
    active_config,
    permissions,
):
    user = user_factory("audit-folder-reviewer", is_superuser=True)
    client.force_login(user)
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Review Audit Film", "markets": ["medical"]},
        },
    )
    folder_event = FolderChangeEvent.objects.create(
        event_type=FolderChangeEvent.EventType.ADDED,
        path="Products/Review_Audit_Film/spec.txt",
        matched_record_id=record_response.json()["id"],
    )

    response = post_json(
        client,
        f"/api/folder-events/{folder_event.pk}/accept/",
        {},
        HTTP_X_REQUEST_ID="folder-review-1",
    )

    assert response.status_code == 200
    event = AuditEvent.objects.get(action="folder_event.accepted")
    assert event.object_type == "folderchangeevent"
    assert event.object_id == str(folder_event.pk)
    assert event.before["review_status"] == FolderChangeEvent.ReviewStatus.PENDING
    assert event.after["review_status"] == FolderChangeEvent.ReviewStatus.ACCEPTED
    assert event.after["reviewer_id"] == user.pk
    assert event.request_id == "folder-review-1"


@pytest.mark.django_db
def test_global_audit_list_filters_before_limiting_and_shows_folder_events(
    client,
    user_factory,
    active_config,
    permissions,
):
    engineer = user_factory("audit-list-engineer", "Engineer")
    client.force_login(engineer)
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Visible Audit Film", "markets": ["medical"]},
        },
    )
    visible_record_id = record_response.json()["id"]
    AuditEvent.objects.create(
        actor=engineer,
        action="manual.visible",
        object_type="record",
        object_id=visible_record_id,
        before=None,
        after={"object_type_key": "product"},
    )
    hidden_records = [
        AuditEvent(
            actor=engineer,
            action="hidden.event",
            object_type="record",
            object_id=f"00000000-0000-0000-0000-{index:012d}",
            before=None,
            after=None,
        )
        for index in range(505)
    ]
    AuditEvent.objects.bulk_create(hidden_records)
    folder_event = FolderChangeEvent.objects.create(
        event_type=FolderChangeEvent.EventType.ADDED,
        path="Products/Visible_Audit_Film/spec.txt",
        matched_record_id=visible_record_id,
    )
    review_response = post_json(
        client,
        f"/api/folder-events/{folder_event.pk}/accept/",
        {},
    )

    response = client.get("/api/audit/")

    assert review_response.status_code == 200
    assert response.status_code == 200
    actions = [event["action"] for event in response.json()["results"]]
    assert "manual.visible" in actions
    assert "record.created" in actions
    assert "folder_event.accepted" in actions


@pytest.mark.django_db
def test_import_dry_run_creates_audit_event(
    client,
    user_factory,
    active_config,
    permissions,
):
    user = user_factory("audit-importer", "Engineer")
    job = ImportJob.objects.create(
        source_file=workbook_file(
            [["Code", "Commercial Name", "Category"], ["", "Dry Run Film", "film"]],
            name="dry-run-audit.xlsx",
        ),
        target_object_type="product",
        mapping=import_mapping(),
    )
    client.force_login(user)

    response = client.post(
        f"/api/imports/jobs/{job.pk}/dry-run/",
        HTTP_X_REQUEST_ID="dry-run-request-1",
        HTTP_USER_AGENT="audit-import-agent",
    )

    assert response.status_code == 200
    event = AuditEvent.objects.get(action="import.dry_run")
    assert event.object_type == "importjob"
    assert event.object_id == str(job.pk)
    assert event.before["state"] == ImportJob.State.PENDING
    assert event.after["state"] == ImportJob.State.DRY_RUN_FAILED
    assert event.after["dry_run_results"]["summary"] == {"create": 0, "update": 0, "errors": 1}
    assert event.after["error_rows"][0]["errors"]["markets"] == ["This field is required."]
    assert event.request_id == "dry-run-request-1"
    assert event.user_agent == "audit-import-agent"


@pytest.mark.django_db
def test_import_apply_nested_record_audit_records_request_metadata(
    client,
    user_factory,
    active_config,
    permissions,
):
    user = user_factory("audit-apply-engineer", "Engineer")
    client.force_login(user)
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {
                "commercial_name": "Apply Audit Film",
                "category": "film",
                "markets": ["medical"],
            },
        },
    )
    record_id = record_response.json()["id"]
    job = ImportJob.objects.create(
        source_file=workbook_file(
            [["Code", "Commercial Name", "Category"], ["PROD-000001", "Apply Audit Film", "resin"]],
            name="apply-audit.xlsx",
        ),
        target_object_type="product",
        mapping=import_mapping(),
    )
    dry_run_import(job, actor=user)

    response = client.post(
        f"/api/imports/jobs/{job.pk}/apply/",
        HTTP_X_REQUEST_ID="apply-request-1",
        HTTP_USER_AGENT="audit-apply-agent",
        REMOTE_ADDR="203.0.113.20",
    )

    assert response.status_code == 200
    event = AuditEvent.objects.get(action="record.updated", object_id=record_id)
    assert event.request_id == "apply-request-1"
    assert event.user_agent == "audit-apply-agent"
    assert event.ip_address == "203.0.113.20"
    assert event.after["data"]["category"] == "resin"


@pytest.mark.django_db
def test_folder_link_accept_audit_records_request_metadata(
    client,
    user_factory,
    active_config,
    permissions,
    settings,
    tmp_path,
):
    settings.MANAGED_FILE_ROOT = tmp_path
    legacy_root = tmp_path / "legacy"
    linked_folder = legacy_root / "linked-product"
    linked_folder.mkdir(parents=True)
    user = user_factory("audit-folder-link-admin", "Product Admin")
    client.force_login(user)
    record_response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": "product",
            "data": {"commercial_name": "Linked Audit Film", "markets": ["medical"]},
        },
    )

    response = post_json(
        client,
        "/api/imports/folder-links/accept/",
        {
            "legacy_root_path": str(legacy_root),
            "object_type_key": "product",
            "links": [
                {
                    "record_id": record_response.json()["id"],
                    "relative_path": "linked-product",
                }
            ],
        },
        HTTP_X_REQUEST_ID="folder-link-request-1",
        HTTP_USER_AGENT="audit-folder-link-agent",
    )

    assert response.status_code == 200
    event = AuditEvent.objects.get(action="folder.linked")
    assert event.request_id == "folder-link-request-1"
    assert event.user_agent == "audit-folder-link-agent"
    assert event.after["relative_path"] == "legacy/linked-product"

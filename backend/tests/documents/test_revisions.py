import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from rest_framework import serializers

from apps.accounts.models import ObjectPermission
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
def document_permissions(db):
    ObjectPermission.objects.create(
        role_name="Viewer",
        object_type_key="product",
        can_view=True,
    )
    ObjectPermission.objects.create(
        role_name="Engineer",
        object_type_key="product",
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


@pytest.fixture
def product_record(db):
    return Record.objects.create(
        object_type_key="product",
        code="PROD-000001",
        title="Clear Film",
        schema_version=1,
        data={},
    )


def upload(name, content, content_type="text/plain"):
    return SimpleUploadedFile(name, content, content_type=content_type)


@pytest.mark.django_db
def test_create_document_with_initial_revision_stores_metadata_and_event(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    from apps.documents.models import DocumentEvent, DocumentRevision

    settings.MEDIA_ROOT = tmp_path
    client.force_login(user_factory("doc-engineer", "Engineer"))
    content = b"material safety data"

    response = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Safety Data Sheet",
            "document_type": "sds",
            "revision_label": "A",
            "file": upload("../unsafe.txt", content),
        },
    )

    assert response.status_code == 201
    body = response.json()
    revision = DocumentRevision.objects.get(pk=body["current_revision"]["id"])
    assert body["title"] == "Safety Data Sheet"
    assert body["state"] == "draft"
    assert revision.file_name == "unsafe.txt"
    assert revision.size == len(content)
    assert revision.sha256 == hashlib.sha256(content).hexdigest()
    assert revision.storage_path.startswith(f"documents/{body['id']}/revisions/{revision.pk}/")
    assert revision.extraction_status == "unsupported"
    assert (tmp_path / revision.storage_path).read_bytes() == content
    assert DocumentEvent.objects.filter(
        document_id=body["id"],
        revision=revision,
        action="revision_created",
        actor__username="doc-engineer",
    ).exists()


@pytest.mark.django_db
def test_list_and_retrieve_documents_show_visible_metadata_only(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(user_factory("library-engineer", "Engineer"))
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Polycarbonate Data Sheet",
            "document_type": "tds",
            "revision_label": "A",
            "file": upload("pc-tds.txt", b"polycarbonate density tensile"),
        },
    ).json()
    second_revision = client.post(
        f"/api/documents/{created['id']}/revisions/",
        {
            "revision_label": "B",
            "file": upload("pc-tds-b.txt", b"updated polycarbonate values"),
        },
    )
    assert second_revision.status_code == 201

    client.force_login(user_factory("library-viewer", "Viewer"))
    list_response = client.get("/api/documents/")
    assert list_response.status_code == 200
    assert any(document["id"] == created["id"] for document in list_response.json())
    assert all("revisions" not in document for document in list_response.json())

    retrieve_response = client.get(f"/api/documents/{created['id']}/")
    assert retrieve_response.status_code == 200
    assert retrieve_response.json()["title"] == "Polycarbonate Data Sheet"
    assert [revision["revision_label"] for revision in retrieve_response.json()["revisions"]] == [
        "A",
        "B",
    ]

    filtered_response = client.get(f"/api/documents/?owner_record={product_record.pk}")
    assert filtered_response.status_code == 200
    assert [document["id"] for document in filtered_response.json()] == [created["id"]]

    client.force_login(user_factory("library-no-access"))
    assert client.get("/api/documents/").json() == []
    assert client.get(f"/api/documents/{created['id']}/").status_code == 403


@pytest.mark.django_db
def test_draft_revision_can_be_replaced_by_editor(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    from apps.documents.models import DocumentEvent, DocumentRevision

    settings.MEDIA_ROOT = tmp_path
    client.force_login(user_factory("replace-engineer", "Engineer"))
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Drawing",
            "document_type": "drawing",
            "revision_label": "A",
            "file": upload("drawing.txt", b"first"),
        },
    ).json()

    response = client.post(
        f"/api/documents/{created['id']}/revisions/",
        {
            "revision_label": "A",
            "file": upload("drawing-v2.txt", b"second"),
        },
    )

    assert response.status_code == 201
    assert DocumentRevision.objects.filter(document_id=created["id"], revision_label="A").count() == 1
    revision = DocumentRevision.objects.get(document_id=created["id"], revision_label="A")
    assert revision.file_name == "drawing-v2.txt"
    assert revision.sha256 == hashlib.sha256(b"second").hexdigest()
    assert DocumentEvent.objects.filter(
        document_id=created["id"],
        revision=revision,
        action="revision_replaced",
    ).exists()
    event = DocumentEvent.objects.filter(
        document_id=created["id"],
        revision=revision,
        action="revision_replaced",
    ).latest("timestamp")
    assert event.data["before"]["file_name"] == "drawing.txt"
    assert event.data["after"]["file_name"] == "drawing-v2.txt"


@pytest.mark.django_db
def test_draft_replacement_uses_new_storage_path_and_preserves_old_file(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    from apps.documents.models import DocumentRevision
    from apps.documents.storage import path_for_storage_path

    settings.MEDIA_ROOT = tmp_path
    client.force_login(user_factory("replace-path-engineer", "Engineer"))
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Drawing Path",
            "document_type": "drawing",
            "revision_label": "A",
            "file": upload("same.txt", b"first version"),
        },
    ).json()
    revision = DocumentRevision.objects.get(pk=created["current_revision"]["id"])
    original_path = revision.storage_path
    original_file = path_for_storage_path(original_path)

    response = client.post(
        f"/api/documents/{created['id']}/revisions/",
        {
            "revision_label": "A",
            "file": upload("same.txt", b"second version"),
        },
    )

    revision.refresh_from_db()
    assert response.status_code == 201
    assert revision.storage_path != original_path
    assert original_file.read_bytes() == b"first version"
    assert path_for_storage_path(revision.storage_path).read_bytes() == b"second version"


@pytest.mark.django_db
def test_draft_replacement_rollback_keeps_database_and_old_file_consistent(
    user_factory,
    product_record,
    settings,
    tmp_path,
    monkeypatch,
):
    from apps.documents.models import Document, DocumentRevision
    from apps.documents.storage import path_for_storage_path
    from apps.documents.views import _create_or_replace_revision
    import apps.documents.views as document_views
    from django.db import transaction

    settings.MEDIA_ROOT = tmp_path
    actor = user_factory("rollback-engineer", "Engineer")
    document = Document.objects.create(
        title="Rollback Drawing",
        owner_record=product_record,
        document_type="drawing",
    )
    revision = _create_or_replace_revision(document, "A", upload("same.txt", b"old bytes"), actor)
    original_path = revision.storage_path
    original_file = path_for_storage_path(original_path)
    original_hash = revision.sha256

    def fail_replacement_event(document, revision, action, actor, data=None):
        if action == "revision_replaced":
            raise RuntimeError("event write failed")
        return document_views.DocumentEvent.objects.create(
            document=document,
            revision=revision,
            action=action,
            actor=actor,
            data=data or {},
        )

    monkeypatch.setattr(document_views, "_record_event", fail_replacement_event)

    with pytest.raises(RuntimeError), transaction.atomic():
        _create_or_replace_revision(document, "A", upload("same.txt", b"new bytes"), actor)

    revision = DocumentRevision.objects.get(pk=revision.pk)
    assert revision.storage_path == original_path
    assert revision.sha256 == original_hash
    assert original_file.read_bytes() == b"old bytes"


@pytest.mark.django_db
def test_stale_draft_replace_rechecks_released_state_before_mutating(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
    monkeypatch,
):
    from apps.documents.models import Document, DocumentRevision
    from apps.documents.storage import path_for_storage_path
    from apps.documents.views import _create_or_replace_revision
    import apps.documents.views as document_views

    settings.MEDIA_ROOT = tmp_path
    actor = user_factory("stale-replace-engineer", "Engineer")
    document = Document.objects.create(
        title="Race Spec",
        owner_record=product_record,
        document_type="specification",
    )
    revision = _create_or_replace_revision(document, "A", upload("race.txt", b"draft"), actor)
    original_path = revision.storage_path
    original_hash = revision.sha256
    original_bytes = path_for_storage_path(original_path).read_bytes()
    original_save = document_views.save_uploaded_revision_file

    def release_before_write(*args, **kwargs):
        DocumentRevision.objects.filter(pk=revision.pk).update(state=DocumentRevision.State.RELEASED)
        return original_save(*args, **kwargs)

    monkeypatch.setattr(document_views, "save_uploaded_revision_file", release_before_write)

    with pytest.raises(serializers.ValidationError):
        _create_or_replace_revision(document, "A", upload("race.txt", b"replacement"), actor)

    revision.refresh_from_db()
    assert revision.state == DocumentRevision.State.RELEASED
    assert revision.storage_path == original_path
    assert revision.sha256 == original_hash
    assert path_for_storage_path(original_path).read_bytes() == original_bytes


@pytest.mark.django_db
def test_released_revision_is_immutable_and_new_label_is_required(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    from apps.documents.models import Document, DocumentEvent, DocumentRevision

    settings.MEDIA_ROOT = tmp_path
    engineer = user_factory("immutable-engineer", "Engineer")
    approver = user_factory("immutable-approver", "Approver")
    client.force_login(engineer)
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Specification",
            "document_type": "specification",
            "revision_label": "A",
            "file": upload("spec.txt", b"draft"),
        },
    ).json()
    revision_id = created["current_revision"]["id"]

    client.force_login(approver)
    release_response = client.post(
        f"/api/documents/{created['id']}/revisions/{revision_id}/release/"
    )
    assert release_response.status_code == 200

    client.force_login(engineer)
    replace_response = client.post(
        f"/api/documents/{created['id']}/revisions/",
        {
            "revision_label": "A",
            "file": upload("spec-replace.txt", b"replacement"),
        },
    )
    new_label_response = client.post(
        f"/api/documents/{created['id']}/revisions/",
        {
            "revision_label": "B",
            "file": upload("spec-b.txt", b"next"),
        },
    )

    document = Document.objects.get(pk=created["id"])
    released = DocumentRevision.objects.get(pk=revision_id)
    assert replace_response.status_code == 400
    assert "revision_label" in replace_response.json()
    assert new_label_response.status_code == 201
    assert released.state == "released"
    assert released.released_at is not None
    assert document.state == "released"
    assert document.current_revision_id == revision_id
    assert DocumentEvent.objects.filter(
        document=document,
        revision=released,
        action="revision_released",
        actor=approver,
    ).exists()


@pytest.mark.django_db
def test_document_archive_marks_document_obsolete_and_records_event(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    from apps.documents.models import Document, DocumentEvent

    settings.MEDIA_ROOT = tmp_path
    engineer = user_factory("archive-document-engineer", "Engineer")
    client.force_login(engineer)
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Archive Me",
            "document_type": "specification",
            "revision_label": "A",
            "file": upload("archive.txt", b"archive me"),
        },
    ).json()

    response = client.post(f"/api/documents/{created['id']}/archive/")

    assert response.status_code == 200
    assert response.json()["state"] == "obsolete"
    document = Document.objects.get(pk=created["id"])
    assert document.state == Document.State.OBSOLETE
    assert DocumentEvent.objects.filter(
        document=document,
        action="document_archived",
        actor=engineer,
    ).exists()


@pytest.mark.django_db
def test_release_lock_query_does_not_join_nullable_document_relations(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    from apps.documents.views import DocumentViewSet

    settings.MEDIA_ROOT = tmp_path
    engineer = user_factory("lock-query-engineer", "Engineer")
    client.force_login(engineer)
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Lock Query",
            "document_type": "specification",
            "revision_label": "A",
            "file": upload("lock-query.txt", b"lock me"),
        },
    ).json()

    with CaptureQueriesContext(connection) as queries:
        DocumentViewSet()._lock_document(created["id"])

    document_lock_queries = [
        query["sql"]
        for query in queries
        if 'FROM "documents_document"' in query["sql"]
        and 'WHERE "documents_document"."id"' in query["sql"]
    ]
    assert document_lock_queries
    assert all('"documents_documentrevision"' not in query for query in document_lock_queries)
    assert all('"folders_managedfolder"' not in query for query in document_lock_queries)


@pytest.mark.django_db
def test_document_revision_create_and_release_enqueue_search_indexing(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    from apps.search import tasks

    settings.MEDIA_ROOT = tmp_path
    indexed_revision_ids = []
    monkeypatch.setattr(
        tasks.index_document_revision,
        "delay",
        lambda revision_id: indexed_revision_ids.append(revision_id),
    )
    engineer = user_factory("doc-index-engineer", "Engineer")
    approver = user_factory("doc-index-approver", "Approver")

    with django_capture_on_commit_callbacks(execute=True):
        client.force_login(engineer)
        created = client.post(
            "/api/documents/",
            {
                "owner_record": str(product_record.pk),
                "title": "Indexed Specification",
                "document_type": "specification",
                "revision_label": "A",
                "file": upload("indexed-a.txt", b"draft text"),
            },
        )
        assert created.status_code == 201
        document_id = created.json()["id"]
        first_revision_id = created.json()["current_revision"]["id"]

        added = client.post(
            f"/api/documents/{document_id}/revisions/",
            {
                "revision_label": "B",
                "file": upload("indexed-b.txt", b"release text"),
            },
        )
        assert added.status_code == 201
        second_revision_id = added.json()["id"]

        client.force_login(approver)
        released = client.post(f"/api/documents/{document_id}/revisions/{second_revision_id}/release/")
        assert released.status_code == 200

    assert indexed_revision_ids == [first_revision_id, second_revision_id, second_revision_id]


@pytest.mark.django_db
def test_same_label_integrity_error_returns_conflict_response(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
    monkeypatch,
):
    from apps.documents.models import DocumentRevision

    settings.MEDIA_ROOT = tmp_path
    client.force_login(user_factory("integrity-engineer", "Engineer"))
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Concurrent Spec",
            "document_type": "specification",
        },
    ).json()
    original_create = DocumentRevision.objects.create

    def raise_integrity_once(*args, **kwargs):
        if kwargs.get("revision_label") == "A":
            raise IntegrityError("unique_revision_label_per_document")
        return original_create(*args, **kwargs)

    monkeypatch.setattr(DocumentRevision.objects, "create", raise_integrity_once)

    response = client.post(
        f"/api/documents/{created['id']}/revisions/",
        {
            "revision_label": "A",
            "file": upload("same.txt", b"content"),
        },
    )

    assert response.status_code == 409
    assert response.json()["revision_label"][0] == "Revision label already exists."


@pytest.mark.django_db
def test_sanitized_label_collision_does_not_overwrite_released_revision(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    from apps.documents.models import DocumentRevision
    from apps.documents.storage import path_for_storage_path

    settings.MEDIA_ROOT = tmp_path
    engineer = user_factory("collision-engineer", "Engineer")
    approver = user_factory("collision-approver", "Approver")
    client.force_login(engineer)
    released_content = b"released bytes"
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Collision Specification",
            "document_type": "specification",
            "revision_label": "AB",
            "file": upload("same.txt", released_content),
        },
    ).json()
    released_revision_id = created["current_revision"]["id"]

    client.force_login(approver)
    assert (
        client.post(
            f"/api/documents/{created['id']}/revisions/{released_revision_id}/release/"
        ).status_code
        == 200
    )

    client.force_login(engineer)
    response = client.post(
        f"/api/documents/{created['id']}/revisions/",
        {
            "revision_label": "A/B",
            "file": upload("same.txt", b"new draft bytes"),
        },
    )

    released_revision = DocumentRevision.objects.get(pk=released_revision_id)
    assert response.status_code == 201
    new_revision = DocumentRevision.objects.get(pk=response.json()["id"])
    assert released_revision.storage_path != new_revision.storage_path
    assert released_revision.sha256 == hashlib.sha256(released_content).hexdigest()
    assert path_for_storage_path(released_revision.storage_path).read_bytes() == released_content
    assert path_for_storage_path(new_revision.storage_path).read_bytes() == b"new draft bytes"


@pytest.mark.django_db
def test_release_requires_release_permission(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(user_factory("release-denied-engineer", "Engineer"))
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Protocol",
            "document_type": "protocol",
            "revision_label": "A",
            "file": upload("protocol.txt", b"draft"),
        },
    ).json()

    response = client.post(
        f"/api/documents/{created['id']}/revisions/{created['current_revision']['id']}/release/"
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_download_and_preview_require_view_permission(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(user_factory("view-doc-engineer", "Engineer"))
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Visible Doc",
            "document_type": "note",
            "revision_label": "A",
            "file": upload("visible.txt", b"visible text"),
        },
    ).json()

    client.force_login(user_factory("no-document-role"))
    assert client.get(f"/api/documents/{created['id']}/download/").status_code == 403
    assert client.get(f"/api/documents/{created['id']}/preview/").status_code == 403

    client.force_login(user_factory("document-viewer", "Viewer"))
    download_response = client.get(f"/api/documents/{created['id']}/download/")
    preview_response = client.get(f"/api/documents/{created['id']}/preview/")

    assert download_response.status_code == 200
    assert b"".join(download_response.streaming_content) == b"visible text"
    assert preview_response.status_code == 200
    assert preview_response.json()["file_name"] == "visible.txt"
    assert preview_response.json()["extraction_status"] == "unsupported"


@pytest.mark.django_db
def test_preview_caps_returned_text_and_reports_truncation(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    from apps.documents.models import DocumentRevision

    settings.MEDIA_ROOT = tmp_path
    client.force_login(user_factory("preview-cap-engineer", "Engineer"))
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Long Preview",
            "document_type": "note",
            "revision_label": "A",
            "file": upload("visible.txt", b"visible text"),
        },
    ).json()
    revision = DocumentRevision.objects.get(pk=created["current_revision"]["id"])
    revision.extracted_text = "x" * 20001
    revision.extraction_status = "extracted"
    revision.save(update_fields=["extracted_text", "extraction_status", "updated_at"])

    client.force_login(user_factory("preview-cap-viewer", "Viewer"))
    response = client.get(f"/api/documents/{created['id']}/preview/")

    assert response.status_code == 200
    body = response.json()
    assert len(body["extracted_text"]) == 20000
    assert body["truncated"] is True


@pytest.mark.django_db
def test_download_missing_storage_file_returns_controlled_not_found(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
):
    from apps.documents.models import DocumentEvent, DocumentRevision
    from apps.documents.storage import path_for_storage_path

    settings.MEDIA_ROOT = tmp_path
    client.force_login(user_factory("missing-file-engineer", "Engineer"))
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Missing File",
            "document_type": "note",
            "revision_label": "A",
            "file": upload("missing.txt", b"missing soon"),
        },
    ).json()
    revision = DocumentRevision.objects.get(pk=created["current_revision"]["id"])
    path_for_storage_path(revision.storage_path).unlink()

    client.force_login(user_factory("missing-file-viewer", "Viewer"))
    response = client.get(f"/api/documents/{created['id']}/download/")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document file is missing from storage."
    assert DocumentEvent.objects.filter(
        document_id=created["id"],
        revision=revision,
        action="storage_missing",
    ).exists()


@pytest.mark.django_db
def test_download_file_deleted_after_exists_check_returns_controlled_not_found(
    client,
    user_factory,
    document_permissions,
    product_record,
    settings,
    tmp_path,
    monkeypatch,
):
    from apps.documents.models import DocumentEvent, DocumentRevision
    import apps.documents.views as document_views

    settings.MEDIA_ROOT = tmp_path
    client.force_login(user_factory("missing-open-engineer", "Engineer"))
    created = client.post(
        "/api/documents/",
        {
            "owner_record": str(product_record.pk),
            "title": "Missing During Open",
            "document_type": "note",
            "revision_label": "A",
            "file": upload("missing-open.txt", b"vanishing"),
        },
    ).json()
    revision = DocumentRevision.objects.get(pk=created["current_revision"]["id"])

    class VanishingPath:
        def exists(self):
            return True

        def open(self, *_args, **_kwargs):
            raise FileNotFoundError("removed after exists")

    monkeypatch.setattr(
        document_views,
        "path_for_storage_path",
        lambda storage_path: VanishingPath(),
    )

    client.force_login(user_factory("missing-open-viewer", "Viewer"))
    response = client.get(f"/api/documents/{created['id']}/download/")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document file is missing from storage."
    assert DocumentEvent.objects.filter(
        document_id=created["id"],
        revision=revision,
        action="storage_missing",
    ).exists()

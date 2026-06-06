import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

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

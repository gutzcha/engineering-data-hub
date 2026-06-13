# ===
# File Summary
# Path: backend\tests\search\test_index_payloads.py
# Type: python
# Purpose: Backend test suite validating domain invariants and API behavior.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: user_factory, create_user, search_permissions, test_record_payload_contains_required_fields_data_text_and_relationship_text, test_record_payload_includes_incoming_relationship_text
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
from apps.documents.models import Document, DocumentRevision
from apps.folders.models import FolderChangeEvent
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
def search_permissions(db):
    ObjectPermission.objects.create(
        role_name="Viewer",
        object_type_key="product",
        can_view=True,
    )


@pytest.mark.django_db
def test_record_payload_contains_required_fields_data_text_and_relationship_text():
    from apps.search.indexers import build_record_payload

    raw_material = Record.objects.create(
        object_type_key="raw_material",
        code="MAT-2026-0001",
        title="PCR Resin",
        schema_version=1,
        data={"supplier": "North Plant"},
    )
    record = Record.objects.create(
        object_type_key="product",
        code="PROD-000001",
        title="Clear Film",
        schema_version=1,
        data={
            "commercial_name": "Clear Film",
            "grade": 12.5,
            "markets": ["medical", "industrial"],
            "properties": {"color": "transparent", "recyclable": True},
            "empty": None,
        },
    )
    Relationship.objects.create(
        source_record=record,
        target_record=raw_material,
        relationship_type_key="uses_material",
    )

    payload = build_record_payload(record)

    assert payload["id"] == str(record.pk)
    assert payload["object_type_key"] == "product"
    assert payload["code"] == "PROD-000001"
    assert payload["title"] == "Clear Film"
    assert payload["status"] == "draft"
    assert payload["updated_at"] == record.updated_at.isoformat()
    assert "commercial_name" not in payload["data_text"]
    assert "Clear Film" in payload["data_text"]
    assert "12.5" in payload["data_text"]
    assert "medical" in payload["data_text"]
    assert "transparent" in payload["data_text"]
    assert "True" in payload["data_text"]
    assert "MAT-2026-0001" in payload["relationship_text"]
    assert "PCR Resin" in payload["relationship_text"]
    assert "raw_material" in payload["relationship_text"]
    assert "uses_material" in payload["relationship_text"]


@pytest.mark.django_db
def test_record_payload_includes_incoming_relationship_text():
    from apps.search.indexers import build_record_payload

    product = Record.objects.create(
        object_type_key="product",
        code="PROD-000001",
        title="Clear Film",
        schema_version=1,
        data={},
    )
    component = Record.objects.create(
        object_type_key="component",
        code="COMP-000001",
        title="Cap Layer",
        schema_version=1,
        data={},
    )
    Relationship.objects.create(
        source_record=component,
        target_record=product,
        relationship_type_key="part_of",
    )

    payload = build_record_payload(product)

    assert "COMP-000001" in payload["relationship_text"]
    assert "Cap Layer" in payload["relationship_text"]
    assert "component" in payload["relationship_text"]
    assert "part_of" in payload["relationship_text"]


@pytest.mark.django_db
def test_document_revision_payload_contains_required_fields_and_extracted_text():
    from apps.search.indexers import build_document_revision_payload

    record = Record.objects.create(
        object_type_key="product",
        code="PROD-000001",
        title="Clear Film",
        schema_version=1,
        data={},
    )
    document = Document.objects.create(
        title="Safety Data Sheet",
        owner_record=record,
        document_type="sds",
    )
    revision = DocumentRevision.objects.create(
        document=document,
        revision_label="A",
        file_name="sds.pdf",
        storage_path="documents/1/revisions/1/sds.pdf",
        sha256="a" * 64,
        extracted_text="Wear gloves during handling.",
        state=DocumentRevision.State.RELEASED,
    )

    payload = build_document_revision_payload(revision)

    assert payload == {
        "id": str(revision.pk),
        "document_id": str(document.pk),
        "record_id": str(record.pk),
        "title": "Safety Data Sheet",
        "revision": "A",
        "state": "released",
        "filename": "sds.pdf",
        "extracted_text": "Wear gloves during handling.",
        "updated_at": revision.updated_at.isoformat(),
    }


@pytest.mark.django_db
def test_index_tasks_use_injected_client_without_live_meilisearch(monkeypatch):
    from apps.search import tasks
    from apps.search.indexers import DOCUMENTS_INDEX, FOLDER_EVENTS_INDEX, RECORDS_INDEX

    calls = []

    class FakeClient:
        enabled = True

        def add_documents(self, index_name, documents):
            calls.append((index_name, documents))

    monkeypatch.setattr(tasks, "get_search_client", lambda: FakeClient())

    record = Record.objects.create(
        object_type_key="product",
        code="PROD-000001",
        title="Clear Film",
        schema_version=1,
        data={"commercial_name": "Clear Film"},
    )
    document = Document.objects.create(
        title="Safety Data Sheet",
        owner_record=record,
        document_type="sds",
    )
    revision = DocumentRevision.objects.create(
        document=document,
        revision_label="A",
        file_name="sds.txt",
        storage_path="documents/1/revisions/1/sds.txt",
        sha256="b" * 64,
        extracted_text="indexed text",
    )
    folder_event = FolderChangeEvent.objects.create(
        event_type=FolderChangeEvent.EventType.ADDED,
        path="Products/PROD-000001/spec.txt",
        matched_record=record,
    )

    tasks.index_record(record.pk)
    tasks.index_document_revision(revision.pk)
    tasks.index_folder_event(folder_event.pk)
    tasks.index_record("00000000-0000-0000-0000-000000000000")
    tasks.index_document_revision(999999)
    tasks.index_folder_event(999999)

    assert calls[0][0] == RECORDS_INDEX
    assert calls[0][1][0]["id"] == str(record.pk)
    assert calls[1][0] == DOCUMENTS_INDEX
    assert calls[1][1][0]["id"] == str(revision.pk)
    assert calls[2][0] == FOLDER_EVENTS_INDEX
    assert calls[2][1][0]["id"] == str(folder_event.pk)
    assert len(calls) == 3


def test_disabled_client_noops_when_meili_url_is_blank(settings):
    from apps.search.client import SearchClient

    settings.MEILI_URL = ""

    client = SearchClient()

    assert client.enabled is False
    assert client.add_documents("records", [{"id": "1"}]) is None
    assert client.delete_all_documents("records") is None
    assert client.search("records", "film") == {"hits": []}


@pytest.mark.django_db
def test_enqueue_helpers_run_index_tasks_after_commit(
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    from apps.search import tasks

    calls = []
    monkeypatch.setattr(tasks.index_record, "delay", lambda record_id: calls.append(("record", record_id)))
    monkeypatch.setattr(
        tasks.index_document_revision,
        "delay",
        lambda revision_id: calls.append(("document", revision_id)),
    )
    monkeypatch.setattr(
        tasks.index_folder_event,
        "delay",
        lambda event_id: calls.append(("folder_event", event_id)),
    )

    with django_capture_on_commit_callbacks(execute=True):
        tasks.enqueue_record_index("record-1")
        tasks.enqueue_record_indexes(["record-2", "record-3"])
        tasks.enqueue_document_revision_index(42)
        tasks.enqueue_folder_event_index(43)
        tasks.enqueue_folder_event_indexes([44, 45])

    assert calls == [
        ("record", "record-1"),
        ("record", "record-2"),
        ("record", "record-3"),
        ("document", 42),
        ("folder_event", 43),
        ("folder_event", 44),
        ("folder_event", 45),
    ]


def test_client_returns_empty_search_for_malformed_meili_response(settings, monkeypatch):
    from apps.search import client as search_client
    from apps.search.client import SearchClient

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"<html>bad gateway</html>"

    settings.MEILI_URL = "http://meili.test"
    monkeypatch.setattr(search_client.request, "urlopen", lambda *args, **kwargs: FakeResponse())

    client = SearchClient()

    assert client.search("records", "film") == {"hits": []}
    assert client.add_documents("records", [{"id": "1"}]) is None


def test_client_returns_empty_search_for_unexpected_meili_response_shape(settings, monkeypatch):
    from apps.search import client as search_client
    from apps.search.client import SearchClient

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'["not", "a", "search", "object"]'

    settings.MEILI_URL = "http://meili.test"
    monkeypatch.setattr(search_client.request, "urlopen", lambda *args, **kwargs: FakeResponse())

    client = SearchClient()

    assert client.search("records", "film") == {"hits": []}


def test_search_hit_mapping_returns_required_record_response_fields():
    from apps.search.views import map_search_hit

    result = map_search_hit(
        "records",
        {
            "id": "record-1",
            "title": "Clear Film",
            "code": "PROD-000001",
            "object_type_key": "product",
            "status": "draft",
            "_formatted": {"data_text": "clear <em>film</em> sheet"},
        },
    )

    assert result == {
        "type": "record",
        "title": "Clear Film",
        "code": "PROD-000001",
        "snippet": "clear <em>film</em> sheet",
        "object_type_key": "product",
        "status": "draft",
        "url": "/records/record-1",
    }


def test_search_hit_mapping_returns_required_document_response_fields():
    from apps.search.views import map_search_hit

    result = map_search_hit(
        "documents",
        {
            "id": "revision-1",
            "document_id": "document-1",
            "record_id": "record-1",
            "title": "Safety Data Sheet",
            "revision": "A",
            "state": "released",
            "filename": "sds.pdf",
            "_formatted": {"extracted_text": "wear <em>gloves</em>"},
        },
    )

    assert result == {
        "type": "document",
        "title": "Safety Data Sheet",
        "code": "sds.pdf",
        "snippet": "wear <em>gloves</em>",
        "object_type_key": "",
        "status": "released",
        "url": "/documents/document-1",
    }


@pytest.mark.django_db
def test_search_api_returns_empty_results_for_blank_query(client, user_factory):
    client.force_login(user_factory("blank-search-user"))

    response = client.get("/api/search/?q=   ")

    assert response.status_code == 200
    assert response.json() == {"results": []}


@pytest.mark.django_db
def test_search_api_maps_fake_hits_and_filters_record_permissions(
    client,
    user_factory,
    search_permissions,
    monkeypatch,
):
    import apps.search.views as search_views

    visible_record = Record.objects.create(
        object_type_key="product",
        code="PROD-000001",
        title="Clear Film",
        schema_version=1,
        data={},
    )
    hidden_record = Record.objects.create(
        object_type_key="raw_material",
        code="MAT-000001",
        title="Hidden Resin",
        schema_version=1,
        data={},
    )

    class FakeClient:
        enabled = True

        def search(self, index_name, query, **params):
            assert index_name == "records"
            assert query == "film"
            assert params["attributesToHighlight"] == ["*"]
            return {
                "hits": [
                    {
                        "id": str(visible_record.pk),
                        "title": "Clear Film",
                        "code": "PROD-000001",
                        "object_type_key": "product",
                        "status": "draft",
                        "_formatted": {"data_text": "clear <em>film</em>"},
                    },
                    {
                        "id": str(hidden_record.pk),
                        "title": "Hidden Resin",
                        "code": "MAT-000001",
                        "object_type_key": "raw_material",
                        "status": "draft",
                    },
                ]
            }

    monkeypatch.setattr(search_views, "get_search_client", lambda: FakeClient())
    client.force_login(user_factory("search-viewer", "Viewer"))

    response = client.get("/api/search/?q=film&type=records")

    assert response.status_code == 200
    assert response.json()["results"] == [
        {
            "type": "record",
            "title": "Clear Film",
            "code": "PROD-000001",
            "snippet": "clear <em>film</em>",
            "object_type_key": "product",
            "status": "draft",
            "url": f"/records/{visible_record.pk}",
        }
    ]


@pytest.mark.django_db
def test_search_api_denies_record_hit_when_meili_object_type_disagrees_with_database(
    client,
    user_factory,
    search_permissions,
    monkeypatch,
):
    import apps.search.views as search_views

    hidden_record = Record.objects.create(
        object_type_key="raw_material",
        code="MAT-000001",
        title="Hidden Resin",
        schema_version=1,
        data={},
    )

    class FakeClient:
        enabled = True

        def search(self, index_name, query, **params):
            assert index_name == "records"
            return {
                "hits": [
                    {
                        "id": str(hidden_record.pk),
                        "title": "Leaked Hidden Resin",
                        "code": "MAT-000001",
                        "object_type_key": "product",
                        "status": "draft",
                        "_formatted": {"title": "<em>Leaked</em> Hidden Resin"},
                    }
                ]
            }

    monkeypatch.setattr(search_views, "get_search_client", lambda: FakeClient())
    client.force_login(user_factory("stale-record-viewer", "Viewer"))

    response = client.get("/api/search/?q=resin&type=records")

    assert response.status_code == 200
    assert response.json() == {"results": []}


@pytest.mark.django_db
def test_search_api_denies_folder_event_hit_when_meili_object_type_disagrees_with_database(
    client,
    user_factory,
    search_permissions,
    monkeypatch,
):
    import apps.search.views as search_views

    hidden_record = Record.objects.create(
        object_type_key="raw_material",
        code="MAT-000001",
        title="Hidden Resin",
        schema_version=1,
        data={},
    )
    event = FolderChangeEvent.objects.create(
        event_type=FolderChangeEvent.EventType.ADDED,
        path="raw/hidden-resin.pdf",
        matched_record=hidden_record,
    )

    class FakeClient:
        enabled = True

        def search(self, index_name, query, **params):
            assert index_name == "folder_events"
            return {
                "hits": [
                    {
                        "id": str(event.pk),
                        "event_type": "added",
                        "path": "leaked/hidden-resin.pdf",
                        "review_status": "pending",
                        "object_type_key": "product",
                        "record_id": str(hidden_record.pk),
                        "_formatted": {"path": "<em>leaked</em>/hidden-resin.pdf"},
                    }
                ]
            }

    monkeypatch.setattr(search_views, "get_search_client", lambda: FakeClient())
    client.force_login(user_factory("stale-folder-event-viewer", "Viewer"))

    response = client.get("/api/search/?q=resin&type=folder_events")

    assert response.status_code == 200
    assert response.json() == {"results": []}


@pytest.mark.django_db
def test_search_api_hides_unmatched_folder_events_from_normal_users(
    client,
    user_factory,
    monkeypatch,
):
    import apps.search.views as search_views

    class FakeClient:
        enabled = True

        def search(self, index_name, query, **params):
            assert index_name == "folder_events"
            return {
                "hits": [
                    {
                        "id": "event-1",
                        "event_type": "added",
                        "path": "unmatched/orphan.pdf",
                        "review_status": "pending",
                        "object_type_key": "",
                    }
                ]
            }

    monkeypatch.setattr(search_views, "get_search_client", lambda: FakeClient())
    client.force_login(user_factory("folder-search-user"))

    response = client.get("/api/search/?q=orphan&type=folder_events")

    assert response.status_code == 200
    assert response.json() == {"results": []}


@pytest.mark.django_db
def test_search_api_allows_unmatched_folder_events_for_system_admin_users(
    client,
    user_factory,
    monkeypatch,
):
    import apps.search.views as search_views

    class FakeClient:
        enabled = True

        def search(self, index_name, query, **params):
            assert index_name == "folder_events"
            return {
                "hits": [
                    {
                        "id": "event-1",
                        "event_type": "added",
                        "path": "unmatched/orphan.pdf",
                        "review_status": "pending",
                        "object_type_key": "",
                        "_formatted": {"path": "unmatched/<em>orphan</em>.pdf"},
                    }
                ]
            }

    monkeypatch.setattr(search_views, "get_search_client", lambda: FakeClient())
    client.force_login(user_factory("folder-search-admin", "System Admin"))

    response = client.get("/api/search/?q=orphan&type=folder_events")

    assert response.status_code == 200
    assert response.json()["results"] == [
        {
            "type": "folder_event",
            "title": "unmatched/orphan.pdf",
            "code": "",
            "snippet": "unmatched/<em>orphan</em>.pdf",
            "object_type_key": "",
            "status": "pending",
            "url": "/folder-events/event-1",
        }
    ]


@pytest.mark.django_db
def test_search_api_denies_project_hits_by_default(client, user_factory, monkeypatch):
    import apps.search.views as search_views

    class FakeClient:
        enabled = True

        def search(self, index_name, query, **params):
            assert index_name == "projects"
            return {
                "hits": [
                    {
                        "id": "project-1",
                        "title": "Secret Launch",
                        "code": "PRJ-001",
                        "status": "active",
                    }
                ]
            }

    monkeypatch.setattr(search_views, "get_search_client", lambda: FakeClient())
    client.force_login(user_factory("project-search-user"))

    response = client.get("/api/search/?q=launch&type=projects")

    assert response.status_code == 200
    assert response.json() == {"results": []}


@pytest.mark.django_db
def test_unknown_search_indexes_are_denied_by_default(user_factory):
    from apps.search.views import _user_can_view_hit

    user = user_factory("unknown-search-user")

    assert _user_can_view_hit(user, "unknown", {"id": "unknown-1"}) is False


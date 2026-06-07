import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import ObjectPermission
from apps.config_registry.services import create_draft_from_current, publish_draft
from apps.documents.models import Document, DocumentRevision
from apps.records.models import Record
from apps.search.indexers import (
    DOCUMENTS_INDEX,
    RECORDS_INDEX,
    build_document_revision_payload,
    build_record_payload,
)
from apps.workflows.models import WorkflowInstance, WorkflowTask


def post_json(client, path, payload):
    return client.post(path, payload, content_type="application/json")


def assert_status(response, expected_status):
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: "
        f"{response.content.decode('utf-8', errors='replace')}"
    )


@pytest.fixture
def system_admin(db):
    User = get_user_model()
    user = User.objects.create_user(username="traceability-admin", password="test-pass")
    group, _created = Group.objects.get_or_create(name="System Admin")
    user.groups.add(group)
    return user


@pytest.fixture
def starter_config(system_admin):
    return publish_draft(create_draft_from_current(system_admin), system_admin)


@pytest.fixture
def extracted_spec_text():
    return "Traceable release PDF text for flame retardant polypropylene acceptance."


@pytest.fixture
def product_spec_pdf(extracted_spec_text):
    return SimpleUploadedFile(
        "traceable-product-spec.pdf",
        _pdf_with_text(extracted_spec_text),
        content_type="application/pdf",
    )


@pytest.mark.django_db
def test_traceability_flow_releases_searches_and_audits_product_spec(
    client,
    monkeypatch,
    product_spec_pdf,
    settings,
    starter_config,
    system_admin,
    tmp_path,
    extracted_spec_text,
):
    settings.MANAGED_FILE_ROOT = tmp_path / "managed"
    settings.MEDIA_ROOT = tmp_path / "media"
    client.force_login(system_admin)

    unique_suffix = "E2E-2201"
    supplier = _create_record(
        client,
        "supplier",
        {
            "supplier_name": f"North Polymer Supply {unique_suffix}",
            "supplier_code": f"NPS-{unique_suffix}",
            "approved_status": "Approved",
        },
    )
    product_name = f"Traceable Film {unique_suffix}"
    product = _create_record(
        client,
        "product",
        {
            "commercial_name": product_name,
            "internal_grade": f"IF-{unique_suffix}",
            "resin_family": "PP",
            "application": "Medical packaging",
            "color": "Natural",
        },
    )

    assert product["code"] == "PROD-000001"
    assert product["title"] == product_name
    assert product["schema_version"] == starter_config.version

    folder_response = client.post(f"/api/records/{product['id']}/folders/generate/")
    assert_status(folder_response, 200)
    folder = folder_response.json()
    assert folder["relative_path"] == f"Products/{product['code']}_{product_name.replace(' ', '_')}"
    assert (settings.MANAGED_FILE_ROOT / folder["relative_path"]).is_dir()

    raw_material = _create_record(
        client,
        "raw_material",
        {
            "supplier_material_code": f"RM-{unique_suffix}",
            "material_family": "Base Resin",
            "supplier": supplier["id"],
            "melt_flow_index": 12.5,
            "density": 0.91,
            "color": "Natural",
        },
    )
    relationship_response = post_json(
        client,
        "/api/relationships/",
        {
            "source_record": product["id"],
            "target_record": raw_material["id"],
            "relationship_type_key": "product_uses_material",
            "data": {"basis": "primary resin"},
        },
    )
    assert_status(relationship_response, 201)

    product_spec = _create_record(
        client,
        "product_spec",
        {
            "spec_number": f"SPEC-{unique_suffix}",
            "product": product["id"],
            "revision": "A",
            "effective_date": "2026-06-07",
            "release_notes": "Initial controlled release.",
        },
    )
    product_spec_relationship = post_json(
        client,
        "/api/relationships/",
        {
            "source_record": product["id"],
            "target_record": product_spec["id"],
            "relationship_type_key": "product_has_spec",
            "data": {"revision": "A"},
        },
    )
    assert_status(product_spec_relationship, 201)

    document_response = client.post(
        "/api/documents/",
        {
            "owner_record": product_spec["id"],
            "title": "Controlled Product Spec",
            "document_type": "controlled_document",
            "revision_label": "A",
            "file": product_spec_pdf,
        },
    )
    assert_status(document_response, 201)
    document = document_response.json()
    revision = document["current_revision"]
    assert revision["extraction_status"] == DocumentRevision.ExtractionStatus.EXTRACTED
    assert revision["state"] == DocumentRevision.State.DRAFT

    preview_response = client.get(f"/api/documents/{document['id']}/preview/")
    assert_status(preview_response, 200)
    assert extracted_spec_text in preview_response.json()["extracted_text"]

    workflow_response = client.get(f"/api/records/{product_spec['id']}/workflow/")
    assert_status(workflow_response, 200)
    assert workflow_response.json()["state"] == "draft"

    technical_review = post_json(
        client,
        f"/api/records/{product_spec['id']}/workflow/draft_to_technical_review/",
        {"comment": "Spec package ready for technical review."},
    )
    assert_status(technical_review, 200)
    _complete_task(client, product_spec["id"], "technical_spec_review")

    approval = post_json(
        client,
        f"/api/records/{product_spec['id']}/workflow/technical_review_to_approval/",
        {"comment": "Technical review complete."},
    )
    assert_status(approval, 200)
    _complete_task(client, product_spec["id"], "approver_signoff")

    release_revision_response = post_json(
        client,
        f"/api/documents/{document['id']}/revisions/{revision['id']}/release/",
        {},
    )
    assert_status(release_revision_response, 200)
    assert release_revision_response.json()["state"] == DocumentRevision.State.RELEASED

    release_workflow = post_json(
        client,
        f"/api/records/{product_spec['id']}/workflow/approval_to_released/",
        {"comment": "Controlled document revision released."},
    )
    assert_status(release_workflow, 200)
    assert release_workflow.json()["state"] == "released"

    refreshed_product = Record.objects.get(pk=product["id"])
    refreshed_revision = DocumentRevision.objects.select_related("document__owner_record").get(
        pk=revision["id"]
    )
    search_viewer = _create_search_viewer()
    client.force_login(search_viewer)
    monkeypatch.setattr(
        "apps.search.views.get_search_client",
        lambda: FakeSearchClient(refreshed_product, refreshed_revision),
    )

    product_search = client.get(f"/api/search/?q={product_name}&type=records")
    assert_status(product_search, 200)
    assert product_search.json()["results"] == [
        {
            "type": "record",
            "title": product_name,
            "code": product["code"],
            "snippet": build_record_payload(refreshed_product)["data_text"],
            "object_type_key": "product",
            "status": "draft",
            "url": f"/records/{product['id']}",
        }
    ]

    document_search = client.get("/api/search/?q=flame%20retardant%20polypropylene&type=documents")
    assert_status(document_search, 200)
    assert document_search.json()["results"] == [
        {
            "type": "document",
            "title": "Controlled Product Spec",
            "code": "traceable-product-spec.pdf",
            "snippet": extracted_spec_text,
            "object_type_key": "product_spec",
            "status": "released",
            "url": f"/documents/{document['id']}",
        }
    ]

    audit_response = client.get("/api/audit/?limit=100")
    assert_status(audit_response, 200)
    actions = [event["action"] for event in audit_response.json()["results"]]
    assert {
        "record.created",
        "folder.generated",
        "relationship.created",
        "document.created",
        "workflow.transition_performed",
        "workflow.task_completed",
        "document.revision_released",
    }.issubset(actions)
    assert actions.count("workflow.transition_performed") >= 3
    assert actions.count("workflow.task_completed") >= 2

    product_spec_instance = WorkflowInstance.objects.get(record_id=product_spec["id"])
    assert product_spec_instance.state == "released"
    assert WorkflowTask.objects.filter(
        instance=product_spec_instance,
        key="approver_signoff",
        state=WorkflowTask.State.DONE,
    ).exists()
    assert Document.objects.get(pk=document["id"]).state == Document.State.RELEASED


class FakeSearchClient:
    enabled = True

    def __init__(self, product, revision):
        self.product_payload = build_record_payload(product)
        self.revision_payload = build_document_revision_payload(revision)

    def search(self, index_name, query, **_params):
        if index_name == RECORDS_INDEX:
            return {"hits": self._matching_hits([self.product_payload], query, "data_text")}
        if index_name == DOCUMENTS_INDEX:
            return {"hits": self._matching_hits([self.revision_payload], query, "extracted_text")}
        return {"hits": []}

    def _matching_hits(self, payloads, query, formatted_field):
        normalized_query = query.lower()
        matches = []
        for payload in payloads:
            searchable = " ".join(str(value) for value in payload.values()).lower()
            if normalized_query in searchable:
                matches.append({**payload, "_formatted": {formatted_field: payload[formatted_field]}})
        return matches


def _create_record(client, object_type_key, data):
    response = post_json(
        client,
        "/api/records/",
        {
            "object_type_key": object_type_key,
            "data": data,
        },
    )
    assert_status(response, 201)
    return response.json()


def _create_search_viewer():
    User = get_user_model()
    role_name = "Traceability Viewer"
    group, _created = Group.objects.get_or_create(name=role_name)
    for object_type_key in ("product", "product_spec"):
        ObjectPermission.objects.update_or_create(
            role_name=role_name,
            object_type_key=object_type_key,
            defaults={"can_view": True},
        )
    user = User.objects.create_user(username="traceability-search-viewer", password="test-pass")
    user.groups.add(group)
    return user


def _complete_task(client, record_id, task_key):
    tasks_response = client.get("/api/workflow-tasks/?state=open")
    assert_status(tasks_response, 200)
    task = next(
        (
            item
            for item in tasks_response.json()
            if item["key"] == task_key and item["related_record"] == record_id
        ),
        None,
    )
    assert task is not None, json.dumps(tasks_response.json(), indent=2)
    complete_response = post_json(
        client,
        f"/api/workflow-tasks/{task['id']}/complete/",
        {"comment": f"Completed {task_key} for acceptance test."},
    )
    assert_status(complete_response, 200)
    assert complete_response.json()["state"] == WorkflowTask.State.DONE


def _pdf_with_text(text):
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    content = DecodedStreamObject()
    content.set_data(f"BT /F1 16 Tf 72 720 Td ({text}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(content)

    from io import BytesIO

    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    assert text in (PdfReader(buffer).pages[0].extract_text() or "")
    buffer.seek(0)
    return buffer.read()

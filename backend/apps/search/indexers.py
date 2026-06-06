from collections.abc import Iterable


RECORDS_INDEX = "records"
DOCUMENTS_INDEX = "documents"
PROJECTS_INDEX = "projects"
FOLDER_EVENTS_INDEX = "folder_events"
INDEX_NAMES = (RECORDS_INDEX, DOCUMENTS_INDEX, PROJECTS_INDEX, FOLDER_EVENTS_INDEX)


def build_record_payload(record):
    return {
        "id": str(record.pk),
        "object_type_key": record.object_type_key,
        "code": record.code,
        "title": record.title,
        "status": record.status,
        "data_text": " ".join(_iter_json_values(record.data)),
        "relationship_text": _relationship_text(record),
        "updated_at": record.updated_at.isoformat(),
    }


def build_document_revision_payload(revision):
    document = revision.document
    return {
        "id": str(revision.pk),
        "document_id": str(document.pk),
        "record_id": str(document.owner_record_id),
        "title": document.title,
        "revision": revision.revision_label,
        "state": revision.state,
        "filename": revision.file_name,
        "extracted_text": revision.extracted_text,
        "updated_at": revision.updated_at.isoformat(),
    }


def build_folder_event_payload(event):
    matched_record = event.matched_record
    return {
        "id": str(event.pk),
        "event_type": event.event_type,
        "path": event.path,
        "review_status": event.review_status,
        "record_id": str(event.matched_record_id) if event.matched_record_id else "",
        "record_code": matched_record.code if matched_record else "",
        "record_title": matched_record.title if matched_record else "",
        "object_type_key": matched_record.object_type_key if matched_record else "",
        "updated_at": event.updated_at.isoformat(),
    }


def _iter_json_values(value) -> Iterable[str]:
    if value is None:
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_json_values(item)
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_json_values(item)
        return
    if isinstance(value, tuple):
        for item in value:
            yield from _iter_json_values(item)
        return
    if isinstance(value, bool):
        yield str(value)
        return
    if isinstance(value, int | float | str):
        text = str(value).strip()
        if text:
            yield text


def _relationship_text(record):
    parts = []
    for relationship in record.outgoing_relationships.select_related("target_record"):
        parts.extend(_relationship_parts(relationship.relationship_type_key, relationship.target_record))
    for relationship in record.incoming_relationships.select_related("source_record"):
        parts.extend(_relationship_parts(relationship.relationship_type_key, relationship.source_record))
    return " ".join(parts)


def _relationship_parts(relationship_type_key, related_record):
    return [
        relationship_type_key,
        related_record.code,
        related_record.title,
        related_record.object_type_key,
    ]


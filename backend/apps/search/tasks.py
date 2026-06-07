from celery import shared_task
from django.db import transaction

from apps.search.client import get_search_client
from apps.search.indexers import (
    DOCUMENTS_INDEX,
    FOLDER_EVENTS_INDEX,
    RECORDS_INDEX,
    build_document_revision_payload,
    build_folder_event_payload,
    build_record_payload,
)


BATCH_SIZE = 500


@shared_task
def index_record(record_id):
    from apps.records.models import Record

    try:
        record = Record.objects.get(pk=record_id)
    except (Record.DoesNotExist, ValueError):
        return None
    client = get_search_client()
    if not client.enabled:
        return None
    return client.add_documents(RECORDS_INDEX, [build_record_payload(record)])


@shared_task
def index_document_revision(revision_id):
    from apps.documents.models import DocumentRevision

    try:
        revision = DocumentRevision.objects.select_related("document").get(pk=revision_id)
    except DocumentRevision.DoesNotExist:
        return None
    client = get_search_client()
    if not client.enabled:
        return None
    return client.add_documents(DOCUMENTS_INDEX, [build_document_revision_payload(revision)])


@shared_task
def index_folder_event(event_id):
    from apps.folders.models import FolderChangeEvent

    try:
        event = FolderChangeEvent.objects.select_related("matched_record").get(pk=event_id)
    except FolderChangeEvent.DoesNotExist:
        return None
    client = get_search_client()
    if not client.enabled:
        return None
    return client.add_documents(FOLDER_EVENTS_INDEX, [build_folder_event_payload(event)])


def enqueue_record_index(record_id):
    transaction.on_commit(lambda: index_record.delay(str(record_id)))


def enqueue_record_indexes(record_ids):
    ids = [str(record_id) for record_id in record_ids]
    if not ids:
        return
    transaction.on_commit(lambda: [index_record.delay(record_id) for record_id in ids])


def enqueue_document_revision_index(revision_id):
    transaction.on_commit(lambda: index_document_revision.delay(revision_id))


def enqueue_folder_event_index(event_id):
    transaction.on_commit(lambda: index_folder_event.delay(event_id))


def enqueue_folder_event_indexes(event_ids):
    ids = list(event_ids)
    if not ids:
        return
    transaction.on_commit(lambda: [index_folder_event.delay(event_id) for event_id in ids])


@shared_task
def rebuild_all_indexes():
    from apps.documents.models import DocumentRevision
    from apps.folders.models import FolderChangeEvent
    from apps.records.models import Record

    client = get_search_client()
    if not client.enabled:
        return {"records": 0, "documents": 0, "folder_events": 0, "projects": 0}

    counts = {"records": 0, "documents": 0, "folder_events": 0, "projects": 0}
    for index_name in (RECORDS_INDEX, DOCUMENTS_INDEX, FOLDER_EVENTS_INDEX):
        client.delete_all_documents(index_name)

    for batch in _batched(Record.objects.all().iterator(), BATCH_SIZE):
        client.add_documents(RECORDS_INDEX, [build_record_payload(record) for record in batch])
        counts["records"] += len(batch)

    revision_queryset = DocumentRevision.objects.select_related("document")
    for batch in _batched(revision_queryset.iterator(), BATCH_SIZE):
        client.add_documents(
            DOCUMENTS_INDEX,
            [build_document_revision_payload(revision) for revision in batch],
        )
        counts["documents"] += len(batch)

    event_queryset = FolderChangeEvent.objects.select_related("matched_record")
    for batch in _batched(event_queryset.iterator(), BATCH_SIZE):
        client.add_documents(
            FOLDER_EVENTS_INDEX,
            [build_folder_event_payload(event) for event in batch],
        )
        counts["folder_events"] += len(batch)

    return counts


def _batched(items, batch_size):
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch

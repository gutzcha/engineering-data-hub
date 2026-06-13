"""
Client-readiness smoke checks for the Plastic Engineering Data Hub.

Run inside the backend container:
    python scripts/client_readiness_smoke.py
"""

from __future__ import annotations

import os
import re
import sys


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plastic_hub.settings.dev")

import django  # noqa: E402


django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from apps.documents.models import Document  # noqa: E402
from apps.records.models import Record  # noqa: E402


MIN_PROJECT_RECORDS = 3
MIN_LINKED_DOCUMENTS = 30
REQUIRED_USERS = {"operations_admin", "process_engineer", "quality_manager", "read_only_auditor"}
BLOCKED_PHRASES = (
    "client-readiness",
    "qa-client",
    "operator-search",
    "pw-rm-",
    "pw traceable",
    "prj-demo",
    "sup-demo",
    "client_demo",
    "client-demo",
)
DEMO_WORD = re.compile(r"\bdemo\b", re.IGNORECASE)


def main() -> int:
    failures: list[str] = []
    User = get_user_model()

    users = set(User.objects.filter(is_active=True).values_list("username", flat=True))
    missing_users = REQUIRED_USERS - users
    if missing_users:
        failures.append(f"Missing release users: {', '.join(sorted(missing_users))}")

    active_records = Record.objects.all()
    project_records = active_records.filter(object_type_key="project")
    if project_records.count() < MIN_PROJECT_RECORDS:
        failures.append(f"Expected at least {MIN_PROJECT_RECORDS} project records.")

    linked_documents = Document.objects.exclude(owner_record__isnull=True)
    if linked_documents.count() < MIN_LINKED_DOCUMENTS:
        failures.append(f"Expected at least {MIN_LINKED_DOCUMENTS} linked documents.")

    orphan_documents = Document.objects.filter(owner_record__isnull=True).count()
    if orphan_documents:
        failures.append(f"Found {orphan_documents} documents without an owner record.")

    for label, text in visible_text_samples(active_records, linked_documents):
        lowered = text.lower()
        for phrase in BLOCKED_PHRASES:
            if phrase in lowered:
                failures.append(f"{label} contains blocked phrase '{phrase}'.")
        if DEMO_WORD.search(text):
            failures.append(f"{label} contains client-facing demo wording.")

    if failures:
        print("Client-readiness smoke: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Client-readiness smoke: PASS")
    print(f"- Active users checked: {len(REQUIRED_USERS)} required accounts present")
    print(f"- Project records: {project_records.count()}")
    print(f"- Linked documents: {linked_documents.count()}")
    return 0


def visible_text_samples(records, documents):
    for record in records.iterator():
        yield f"record {record.pk}", " ".join(
            [
                str(record.code or ""),
                str(record.title or ""),
                str(record.object_type_key or ""),
                str(record.status or ""),
                str(record.data or ""),
            ]
        )
    for document in documents.iterator():
        yield f"document {document.pk}", " ".join(
            [
                str(document.title or ""),
                str(document.document_type or ""),
                str(getattr(document, "source_filename", "") or getattr(document, "filename", "") or ""),
            ]
        )


if __name__ == "__main__":
    sys.exit(main())

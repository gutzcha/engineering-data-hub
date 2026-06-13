# ===
# File Summary
# Path: backend\apps\documents\storage.py
# Type: python
# Purpose: Document domain service managing records, revisions, and extraction workflows.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: DocumentStorageError, save_uploaded_revision_file, finalize_uploaded_revision_file, discard_uploaded_revision_file, discard_finalized_revision_file
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

import hashlib
import os
from pathlib import Path, PurePath
from uuid import uuid4

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename


class DocumentStorageError(ValueError):
    pass


def save_uploaded_revision_file(document_id, revision_id, uploaded_file: UploadedFile):
    file_name = _safe_file_name(uploaded_file.name)
    safe_revision_id = _safe_path_part(revision_id)
    upload_id = uuid4().hex
    storage_path = (
        Path("documents")
        / str(document_id)
        / "revisions"
        / safe_revision_id
        / upload_id
        / file_name
    )
    staged_path = Path("documents") / str(document_id) / ".staging" / upload_id / file_name
    staged_absolute_path = _media_path(staged_path)
    staged_absolute_path.parent.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256()
    size = 0
    with staged_absolute_path.open("wb") as handle:
        for chunk in uploaded_file.chunks():
            digest.update(chunk)
            size += len(chunk)
            handle.write(chunk)

    return {
        "file_name": file_name,
        "storage_path": storage_path.as_posix(),
        "sha256": digest.hexdigest(),
        "size": size,
        "mime_type": getattr(uploaded_file, "content_type", "") or "",
        "absolute_path": staged_absolute_path,
        "staged_path": staged_absolute_path,
    }


def finalize_uploaded_revision_file(file_data):
    destination = path_for_storage_path(file_data["storage_path"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(file_data["staged_path"], destination)


def discard_uploaded_revision_file(file_data):
    try:
        Path(file_data["staged_path"]).unlink(missing_ok=True)
    except OSError:
        pass


def discard_finalized_revision_file(file_data):
    try:
        path_for_storage_path(file_data["storage_path"]).unlink(missing_ok=True)
    except OSError:
        pass


def path_for_storage_path(storage_path: str) -> Path:
    return _media_path(Path(storage_path))


def delete_storage_path(storage_path: str):
    try:
        path_for_storage_path(storage_path).unlink(missing_ok=True)
    except OSError:
        pass


def _safe_file_name(file_name: str) -> str:
    name = PurePath(file_name or "document").name
    safe_name = get_valid_filename(name)
    return safe_name or "document"


def _safe_path_part(value: str) -> str:
    safe_value = get_valid_filename(str(value).strip())
    if not safe_value:
        raise DocumentStorageError("Revision label cannot be empty.")
    return safe_value


def _media_path(relative_path: Path) -> Path:
    media_root = Path(settings.MEDIA_ROOT).resolve()
    absolute_path = (media_root / relative_path).resolve()
    if not _is_relative_to(absolute_path, media_root):
        raise DocumentStorageError("Document storage path escaped MEDIA_ROOT.")
    return absolute_path


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


import hashlib
from pathlib import Path, PurePath

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename


class DocumentStorageError(ValueError):
    pass


def save_uploaded_revision_file(document_id, revision_id, uploaded_file: UploadedFile):
    file_name = _safe_file_name(uploaded_file.name)
    safe_revision_id = _safe_path_part(revision_id)
    relative_path = Path("documents") / str(document_id) / "revisions" / safe_revision_id / file_name
    absolute_path = _media_path(relative_path)
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256()
    size = 0
    with absolute_path.open("wb") as handle:
        for chunk in uploaded_file.chunks():
            digest.update(chunk)
            size += len(chunk)
            handle.write(chunk)

    return {
        "file_name": file_name,
        "storage_path": relative_path.as_posix(),
        "sha256": digest.hexdigest(),
        "size": size,
        "mime_type": getattr(uploaded_file, "content_type", "") or "",
        "absolute_path": absolute_path,
    }


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

import hashlib
from pathlib import Path

from django.db import transaction

from apps.folders.models import FolderChangeEvent, FolderFileSnapshot, ManagedFolder
from apps.folders.services import managed_root, managed_path, validate_relative_path


def scan_all_managed_folders():
    events = []
    for managed_folder in ManagedFolder.objects.filter(state=ManagedFolder.State.ACTIVE):
        events.extend(scan_managed_folder(managed_folder))
    return events


def scan_managed_folder(managed_folder):
    root_path = managed_path(managed_folder.relative_path)
    current = _current_file_state(root_path)
    previous = {
        snapshot.path: snapshot
        for snapshot in managed_folder.file_snapshots.all()
    }
    tree_hash = _tree_hash(current)
    if not previous and not managed_folder.last_scan_hash and not current:
        _replace_snapshots(managed_folder, current, tree_hash)
        return []

    events = []
    added_paths = [path for path in current if path not in previous]
    deleted_paths = [path for path in previous if path not in current]
    move_pairs = _detect_moves(added_paths, deleted_paths, current, previous)
    moved_added = {new_path for _old_path, new_path in move_pairs}
    moved_deleted = {old_path for old_path, _new_path in move_pairs}

    with transaction.atomic():
        for old_path, new_path in move_pairs:
            events.append(
                _create_pending_event(
                    managed_folder,
                    FolderChangeEvent.EventType.MOVED,
                    f"{old_path} -> {new_path}",
                    current[new_path]["file_hash"],
                )
            )

        for path in added_paths:
            if path in moved_added:
                continue
            events.append(
                _create_pending_event(
                    managed_folder,
                    FolderChangeEvent.EventType.ADDED,
                    path,
                    current[path]["file_hash"],
                )
            )

        for path, file_state in current.items():
            previous_snapshot = previous.get(path)
            if previous_snapshot and previous_snapshot.file_hash != file_state["file_hash"]:
                events.append(
                    _create_pending_event(
                        managed_folder,
                        FolderChangeEvent.EventType.MODIFIED,
                        path,
                        file_state["file_hash"],
                    )
                )

        for path in deleted_paths:
            if path in moved_deleted:
                continue
            events.append(
                _create_pending_event(
                    managed_folder,
                    FolderChangeEvent.EventType.DELETED,
                    path,
                    previous[path].file_hash,
                )
            )

        _replace_snapshots(managed_folder, current, tree_hash)

    return events


def _current_file_state(root_path):
    if not root_path.exists():
        return {}
    managed_file_root = managed_root()
    files = {}
    for path in sorted(candidate for candidate in root_path.rglob("*") if candidate.is_file()):
        resolved_path = path.resolve()
        if managed_file_root != resolved_path and managed_file_root not in resolved_path.parents:
            continue
        relative_path = resolved_path.relative_to(managed_file_root).as_posix()
        validate_relative_path(relative_path)
        stat = resolved_path.stat()
        files[relative_path] = {
            "file_hash": _file_hash(resolved_path),
            "size": stat.st_size,
            "modified_ns": stat.st_mtime_ns,
        }
    return files


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_hash(current):
    digest = hashlib.sha256()
    for path, state in sorted(current.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(state["file_hash"].encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _detect_moves(added_paths, deleted_paths, current, previous):
    deleted_by_hash = {}
    for path in deleted_paths:
        deleted_by_hash.setdefault(previous[path].file_hash, []).append(path)

    pairs = []
    for new_path in added_paths:
        old_paths = deleted_by_hash.get(current[new_path]["file_hash"], [])
        if old_paths:
            pairs.append((old_paths.pop(0), new_path))
    return pairs


def _create_pending_event(managed_folder, event_type, path, detected_hash):
    event, _created = FolderChangeEvent.objects.get_or_create(
        event_type=event_type,
        path=path,
        detected_hash=detected_hash,
        review_status=FolderChangeEvent.ReviewStatus.PENDING,
        defaults={
            "managed_folder": managed_folder,
            "matched_record": managed_folder.record,
        },
    )
    return event


def _replace_snapshots(managed_folder, current, tree_hash):
    managed_folder.file_snapshots.all().delete()
    FolderFileSnapshot.objects.bulk_create(
        [
            FolderFileSnapshot(
                managed_folder=managed_folder,
                path=path,
                file_hash=state["file_hash"],
                size=state["size"],
                modified_ns=state["modified_ns"],
            )
            for path, state in sorted(current.items())
        ]
    )
    managed_folder.last_scan_hash = tree_hash
    managed_folder.save(update_fields=["last_scan_hash", "updated_at"])

import hashlib
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.db import transaction

from apps.folders.models import FolderChangeEvent, ManagedFolder
from apps.folders.templates import TEMPLATE_CHILDREN, default_template_key, render_folder_template


EMPTY_TREE_HASH = hashlib.sha256().hexdigest()


class ManagedFolderCollisionError(Exception):
    def __init__(self, relative_path):
        self.relative_path = relative_path
        super().__init__(f"Managed folder target already exists: {relative_path}")


def generate_managed_folder(record, *, template_key=None, actor=None):
    template_key = template_key or default_template_key(record.object_type_key)
    if not template_key:
        raise ValueError(f"No managed folder template for {record.object_type_key}.")

    rendered = render_folder_template(record, template_key)
    root_relative_path = rendered.root
    existing_managed_folder = ManagedFolder.objects.filter(
        record=record,
        folder_role="primary",
    ).first()
    if existing_managed_folder and _existing_folder_matches_current_root(existing_managed_folder):
        return existing_managed_folder

    root_path = managed_path(root_relative_path)
    collision_path = None
    if root_path.exists():
        collision_path = root_relative_path
        root_relative_path = _append_record_suffix(root_relative_path, record.id.hex[:8])
        root_path = managed_path(root_relative_path)
        if root_path.exists():
            _record_collision_event(record, collision_path, actor=actor)
            raise ManagedFolderCollisionError(root_relative_path)

    child_relative_paths = _children_for_root(template_key, root_relative_path)

    try:
        with transaction.atomic():
            try:
                root_path.mkdir(parents=True, exist_ok=False)
            except FileExistsError as error:
                raise ManagedFolderCollisionError(root_relative_path) from error
            for child_relative_path in child_relative_paths:
                try:
                    managed_path(child_relative_path).mkdir(parents=True, exist_ok=False)
                except FileExistsError as error:
                    raise ManagedFolderCollisionError(child_relative_path) from error

            managed_folder, _created = ManagedFolder.objects.update_or_create(
                record=record,
                folder_role="primary",
                defaults={
                    "absolute_path": str(root_path),
                    "relative_path": root_relative_path,
                    "template_key": template_key,
                    "state": ManagedFolder.State.ACTIVE,
                    "last_scan_hash": existing_managed_folder.last_scan_hash
                    if existing_managed_folder
                    else EMPTY_TREE_HASH,
                },
            )

            if collision_path:
                _record_collision_event(
                    record,
                    collision_path,
                    actor=actor,
                    managed_folder=managed_folder,
                )
    except ManagedFolderCollisionError as error:
        _record_collision_event(record, collision_path or error.relative_path, actor=actor)
        raise

    return managed_folder


def managed_root():
    return Path(settings.MANAGED_FILE_ROOT).expanduser().resolve()


def managed_path(relative_path):
    safe_relative_path = validate_relative_path(relative_path)
    root = managed_root()
    candidate = root.joinpath(*PurePosixPath(safe_relative_path).parts).resolve(strict=False)
    if candidate != root and root not in candidate.parents:
        raise ValueError("Managed path escapes MANAGED_FILE_ROOT.")
    return candidate


def validate_relative_path(relative_path):
    path = PurePosixPath(str(relative_path))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Managed folder paths must be relative and cannot contain '..'.")
    if any(part in {"", "."} for part in path.parts):
        raise ValueError("Managed folder paths cannot contain empty path segments.")
    return path.as_posix()


def _append_record_suffix(relative_path, suffix):
    parent, _, name = relative_path.rpartition("/")
    suffixed = f"{name}-{suffix}"
    return f"{parent}/{suffixed}" if parent else suffixed


def _children_for_root(template_key, root_relative_path):
    return [f"{root_relative_path}/{child}" for child in TEMPLATE_CHILDREN[template_key]]


def _existing_folder_matches_current_root(managed_folder):
    try:
        expected_path = managed_path(managed_folder.relative_path)
    except ValueError:
        return False
    return expected_path.exists() and Path(managed_folder.absolute_path).resolve(strict=False) == expected_path


def _record_collision_event(record, collision_path, *, actor=None, managed_folder=None):
    event, _created = FolderChangeEvent.objects.get_or_create(
        event_type=FolderChangeEvent.EventType.COLLISION,
        path=collision_path,
        matched_record=record,
        review_status=FolderChangeEvent.ReviewStatus.PENDING,
        defaults={
            "managed_folder": managed_folder,
            "reviewer": actor if actor and actor.is_authenticated else None,
        },
    )
    if managed_folder and not event.managed_folder:
        event.managed_folder = managed_folder
        event.save(update_fields=["managed_folder", "updated_at"])
    return event

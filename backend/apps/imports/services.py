# ===
# File Summary
# Path: backend\apps\imports\services.py
# Type: python
# Purpose: Imports domain for parser/mapping workflows and linked entity updates.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: dry_run_import, apply_import, scan_legacy_folders, accept_folder_links, _preflight_apply_operations
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

from pathlib import Path, PurePosixPath
from types import SimpleNamespace

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.permissions import records_user_can_view, user_can, user_has_view_scope
from apps.audit.services import record_audit_event, snapshot_model
from apps.folders.models import FolderChangeEvent, ManagedFolder
from apps.folders.services import generate_managed_folder, managed_root, validate_relative_path
from apps.imports.mapping import mapped_rows
from apps.imports.models import ImportAuditEvent, ImportJob
from apps.imports.parsers import XlsxParseError, parse_xlsx_rows
from apps.records.models import Record
from apps.records.serializers import RecordSerializer
from apps.records.validation import get_object_type_definition, validate_record_data
from apps.search.tasks import enqueue_folder_event_index, enqueue_record_index


def dry_run_import(job, *, actor=None):
    try:
        rows = mapped_rows(parse_xlsx_rows(job.source_file), job.mapping)
    except XlsxParseError as error:
        job.dry_run_results = {}
        job.error_rows = []
        job.state = ImportJob.State.DRY_RUN_FAILED
        job.save(update_fields=["dry_run_results", "error_rows", "state", "updated_at"])
        raise ValidationError({"source_file": [str(error)]}) from error

    object_type, _active_config = get_object_type_definition(job.target_object_type)
    duplicate_codes = _duplicate_codes(rows)
    unique_duplicates = _duplicate_unique_values(rows, object_type, job.target_object_type)
    creates = []
    updates = []
    error_rows = []

    for row in rows:
        code = row["code"]
        data = row["data"]
        errors = {}
        if code and code in duplicate_codes:
            errors["code"] = ["Duplicate code in import file."]

        existing = _existing_record(job.target_object_type, code) if code else None
        existing_code_owner = _existing_record_by_code(code) if code else None
        if existing_code_owner and existing_code_owner.object_type_key != job.target_object_type:
            errors["code"] = ["Record code already exists on another object type."]
        _add_permission_errors(
            errors,
            actor=actor,
            object_type_key=job.target_object_type,
            code=code,
            existing=existing,
        )
        try:
            validation_data = existing.data.copy() if existing else {}
            validation_data.update(data)
            validate_record_data(
                job.target_object_type,
                validation_data,
                current_record=existing,
            )
        except serializers.ValidationError as error:
            errors.update(_flatten_validation_error(error.detail).get("data", {}))

        for field_key in unique_duplicates.get(row["row_number"], []):
            errors.setdefault(field_key, []).append("Duplicate unique value in import file.")

        if errors:
            error_rows.append(
                {
                    "row_number": row["row_number"],
                    "code": code,
                    "errors": errors,
                }
            )
            continue

        output_row = {"row_number": row["row_number"], "code": code, "data": data}
        if existing:
            output_row["record_id"] = str(existing.pk)
            updates.append(output_row)
        else:
            creates.append(output_row)

    result = {
        "summary": {
            "create": len(creates),
            "update": len(updates),
            "errors": len(error_rows),
        },
        "creates": creates,
        "updates": updates,
        "error_rows": error_rows,
    }
    job.dry_run_results = result
    job.error_rows = error_rows
    job.state = ImportJob.State.DRY_RUN_READY if not error_rows else ImportJob.State.DRY_RUN_FAILED
    job.save(update_fields=["dry_run_results", "error_rows", "state", "updated_at"])
    return result


@transaction.atomic
def apply_import(job, *, actor, create_managed_folders=False, request=None):
    job = ImportJob.objects.select_for_update().get(pk=job.pk)
    if job.state != ImportJob.State.DRY_RUN_READY:
        raise ValueError("Dry-run must pass before apply.")

    result = dry_run_import(job, actor=actor)
    if result["error_rows"]:
        raise ValueError("Dry-run must pass before apply.")

    created = 0
    updated = 0
    serializer_request = request or SimpleNamespace(user=actor)
    operations = _preflight_apply_operations(job, result, serializer_request)

    for operation in operations:
        serializer = operation["serializer"]
        action = operation["action"]
        row_number = operation["row_number"]
        record = serializer.save()
        enqueue_record_index(record.pk)
        ImportAuditEvent.objects.create(
            job=job,
            record=record,
            action=action,
            actor=actor if actor and actor.is_authenticated else None,
            data={"code": record.code, "row_number": row_number},
        )
        if action == ImportAuditEvent.Action.CREATED:
            created += 1
            if create_managed_folders:
                transaction.on_commit(
                    lambda record_id=record.pk: generate_managed_folder(
                        Record.objects.get(pk=record_id),
                        actor=actor,
                        request=request,
                    )
                )
        else:
            updated += 1

    job.created_records_count = created
    job.updated_records_count = updated
    job.error_rows = []
    job.state = ImportJob.State.APPLIED
    job.save(
        update_fields=[
            "created_records_count",
            "updated_records_count",
            "error_rows",
            "state",
            "updated_at",
        ]
    )
    return {"created": created, "updated": updated}


def scan_legacy_folders(*, legacy_root_path, object_type_key, matching_rule):
    legacy_root = Path(legacy_root_path).expanduser().resolve(strict=True)
    root = managed_root()
    if legacy_root != root and root not in legacy_root.parents:
        raise ValueError("Legacy root must be inside MANAGED_FILE_ROOT.")
    records = list(Record.objects.filter(object_type_key=object_type_key).order_by("code"))
    suggestions = []
    unmatched = []
    conflicts = []

    for folder in _iter_leaf_folders(legacy_root):
        relative_path = folder.relative_to(legacy_root).as_posix()
        validate_relative_path(relative_path)
        managed_relative_path = validate_relative_path(folder.relative_to(root).as_posix())
        matches = _matching_records(folder, relative_path, records, matching_rule)
        if len(matches) == 1:
            record = matches[0]
            suggestions.append(
                {
                    "record_id": str(record.pk),
                    "code": record.code,
                    "relative_path": relative_path,
                    "managed_relative_path": managed_relative_path,
                }
            )
        elif len(matches) > 1:
            conflicts.append(
                {
                    "relative_path": relative_path,
                    "managed_relative_path": managed_relative_path,
                    "matched_codes": [record.code for record in matches],
                }
            )
        else:
            unmatched.append(
                {
                    "relative_path": relative_path,
                    "managed_relative_path": managed_relative_path,
                }
            )

    return {
        "suggested_record_links": suggestions,
        "unmatched_folders": unmatched,
        "conflicts": conflicts,
        "accepted_links": [],
    }


@transaction.atomic
def accept_folder_links(*, legacy_root_path, object_type_key, links, actor, request=None):
    legacy_root = Path(legacy_root_path).expanduser().resolve(strict=True)
    root = managed_root()
    if legacy_root != root and root not in legacy_root.parents:
        raise ValueError("Legacy root must be inside MANAGED_FILE_ROOT to accept links.")
    accepted = []

    for link in links:
        record = Record.objects.get(pk=link["record_id"], object_type_key=object_type_key)
        if not user_can(actor, "admin", object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to link folders for this object type.")
        relative_to_legacy = validate_relative_path(link["relative_path"])
        candidate = legacy_root.joinpath(*PurePosixPath(relative_to_legacy).parts).resolve(
            strict=True
        )
        if candidate != legacy_root and legacy_root not in candidate.parents:
            raise ValueError("Linked folder path escapes legacy root.")
        relative_to_managed = validate_relative_path(candidate.relative_to(root).as_posix())
        managed_folder, _created = ManagedFolder.objects.update_or_create(
            record=record,
            folder_role="legacy",
            defaults={
                "absolute_path": str(candidate),
                "relative_path": relative_to_managed,
                "template_key": "legacy_link",
                "state": ManagedFolder.State.ACTIVE,
            },
        )
        event = FolderChangeEvent.objects.create(
            event_type=FolderChangeEvent.EventType.LINK_REQUESTED,
            path=relative_to_managed,
            matched_record=record,
            managed_folder=managed_folder,
            review_status=FolderChangeEvent.ReviewStatus.LINKED,
            reviewer=actor if actor and actor.is_authenticated else None,
        )
        enqueue_folder_event_index(event.pk)
        record_audit_event(
            actor,
            "folder.linked",
            managed_folder,
            before=None,
            after=snapshot_model(
                managed_folder,
                [
                    "id",
                    "record_id",
                    "folder_role",
                    "absolute_path",
                    "relative_path",
                    "template_key",
                    "state",
                ],
            ),
            request=request,
        )
        accepted.append(
            {
                "record_id": str(record.pk),
                "code": record.code,
                "relative_path": relative_to_managed,
            }
        )

    return {"accepted_links": accepted}


def _preflight_apply_operations(job, result, request):
    operations = []
    actor = request.user
    for row in result["updates"]:
        record = Record.objects.get(pk=row["record_id"], object_type_key=job.target_object_type)
        if not user_can(actor, "edit", record.object_type_key, record_id=str(record.pk)):
            raise PermissionDenied("You do not have permission to edit this object type.")
        serializer = RecordSerializer(
            record,
            data={"data": row["data"]},
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        operations.append(
            {
                "serializer": serializer,
                "action": ImportAuditEvent.Action.UPDATED,
                "row_number": row["row_number"],
            }
        )

    for row in result["creates"]:
        code = row["code"]
        if not user_can(actor, "create", job.target_object_type):
            raise PermissionDenied("You do not have permission to create this object type.")
        if code and not user_can(actor, "admin", job.target_object_type):
            raise PermissionDenied("Manual codes for new records require admin permission.")
        payload = {"object_type_key": job.target_object_type, "data": row["data"]}
        if code:
            payload["code"] = code
        serializer = RecordSerializer(data=payload, context={"request": request})
        serializer.is_valid(raise_exception=True)
        operations.append(
            {
                "serializer": serializer,
                "action": ImportAuditEvent.Action.CREATED,
                "row_number": row["row_number"],
            }
        )
    return operations


def _existing_record(object_type_key, code):
    if not code:
        return None
    return Record.objects.filter(object_type_key=object_type_key, code=code).first()


def _existing_record_by_code(code):
    if not code:
        return None
    return Record.objects.filter(code=code).first()


def _duplicate_codes(rows):
    counts = {}
    for row in rows:
        if row["code"]:
            counts[row["code"]] = counts.get(row["code"], 0) + 1
    return {code for code, count in counts.items() if count > 1}


def _duplicate_unique_values(rows, object_type, object_type_key):
    unique_field_keys = [
        field["key"]
        for field in object_type.get("fields", [])
        if field.get("unique") and field.get("key")
    ]
    if not unique_field_keys:
        return {}

    seen = {}
    duplicates = {}
    for row in rows:
        existing = _existing_record(object_type_key, row["code"]) if row["code"] else None
        final_data = existing.data.copy() if existing else {}
        final_data.update(row["data"])
        for field_key in unique_field_keys:
            value = final_data.get(field_key)
            if _is_blank(value):
                continue
            key = (field_key, _hashable_value(value))
            previous_row = seen.get(key)
            if previous_row:
                duplicates.setdefault(previous_row, set()).add(field_key)
                duplicates.setdefault(row["row_number"], set()).add(field_key)
            else:
                seen[key] = row["row_number"]
    return {row_number: sorted(field_keys) for row_number, field_keys in duplicates.items()}


def _add_permission_errors(errors, *, actor, object_type_key, code, existing):
    if actor is None:
        return
    if existing:
        if not user_can(actor, "edit", object_type_key, record_id=str(existing.pk)):
            errors["permission"] = ["You do not have permission to edit this object type."]
        return
    if not user_can(actor, "create", object_type_key):
        errors["permission"] = ["You do not have permission to create this object type."]
    if code and not user_can(actor, "admin", object_type_key):
        errors["code"] = ["Manual codes for new records require admin permission."]


def _hashable_value(value):
    if isinstance(value, list):
        return tuple(value)
    return value


def _is_blank(value):
    return value is None or value == "" or value == []


def _flatten_validation_error(detail):
    if isinstance(detail, dict):
        return {key: _flatten_validation_error(value) for key, value in detail.items()}
    if isinstance(detail, list):
        return [str(item) for item in detail]
    return [str(detail)]


def _iter_leaf_folders(root):
    folders = sorted(path for path in root.rglob("*") if path.is_dir())
    leaf_folders = []
    for folder in folders:
        has_child_directory = any(child.is_dir() for child in folder.iterdir())
        if not has_child_directory:
            leaf_folders.append(folder)
    return leaf_folders


def _matching_records(folder, relative_path, records, matching_rule):
    rule_type = (matching_rule or {}).get("type", "code_in_path")
    haystack = folder.name if rule_type == "filename" else relative_path
    if rule_type == "filename_prefix":
        return [record for record in records if folder.name.startswith(record.code)]
    return [record for record in records if record.code in haystack]


def visible_records_for_export(user, object_type_key):
    get_object_type_definition(object_type_key)
    records = Record.objects.filter(object_type_key=object_type_key).order_by("code")
    if not user_has_view_scope(user, object_type_key):
        raise PermissionDenied("You do not have permission to view this object type.")
    return records_user_can_view(user, records)


def export_timestamp():
    return timezone.now().isoformat()


# ===
# File Summary
# Path: backend\apps\backups\services.py
# Type: python
# Purpose: Backup service managing backup manifests, task scheduling, and restore metadata.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: BackupError, create_backup, run_pg_dump, _generate_backup_id, _validate_backup_id
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
import json
import os
import re
import subprocess
import tarfile
import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections
from django.utils import timezone
from dotenv import dotenv_values

from apps.audit.models import AuditEvent
from apps.backups.models import BackupManifest
from apps.config_registry.models import ConfigurationVersion


SECRET_KEY_PARTS = ("PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL")
BACKUP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
DEFAULT_ENV_KEYS = (
    "APP_ENV",
    "APP_HOST",
    "TIME_ZONE",
    "ALLOWED_HOSTS",
    "SECRET_KEY",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "REDIS_URL",
    "MEILI_MASTER_KEY",
    "MEILI_URL",
    "MANAGED_FILE_ROOT",
    "MEDIA_ROOT",
    "BACKUP_ROOT",
    "CADDY_TLS_DIRECTIVE",
    "CADDY_EMAIL",
)


class BackupError(RuntimeError):
    pass


def create_backup(
    *,
    backup_id=None,
    backup_root=None,
    managed_root=None,
    media_root=None,
    env_file=None,
    database_dump_runner=None,
):
    backup_id = _validate_backup_id(backup_id or _generate_backup_id())
    backup_root = Path(backup_root or settings.BACKUP_ROOT).resolve()
    managed_root = Path(managed_root or settings.MANAGED_FILE_ROOT).resolve()
    media_root = Path(media_root or settings.MEDIA_ROOT).resolve()
    env_file = Path(env_file or getattr(settings, "BACKUP_ENV_FILE", ".env"))
    database_dump_runner = database_dump_runner or run_pg_dump

    backup_dir = (backup_root / backup_id).resolve()
    _ensure_child_path(backup_dir, backup_root)
    backup_dir.mkdir(parents=True, exist_ok=False)

    now = timezone.now()
    manifest = BackupManifest.objects.create(
        backup_id=backup_id,
        started_at=now,
        state=BackupManifest.State.RUNNING,
    )

    paths = {
        "database_dump": backup_dir / "database.dump",
        "managed_files": backup_dir / "managed-files.tar.gz",
        "media_files": backup_dir / "media-files.tar.gz",
        "published_configuration": backup_dir / "published-configuration.json",
        "audit_events": backup_dir / "audit-events.json",
        "env_fingerprint": backup_dir / "env-fingerprint.json",
    }

    try:
        database_dump_runner(paths["database_dump"])
        _write_archive(managed_root, paths["managed_files"])
        _write_archive(media_root, paths["media_files"])
        _write_published_configuration(paths["published_configuration"])
        _write_audit_export(paths["audit_events"])
        _write_env_fingerprint(paths["env_fingerprint"], env_file)

        sha256_manifest = _build_sha256_manifest(backup_id, paths)
        _write_json(backup_dir / "sha256-manifest.json", sha256_manifest)

        manifest.database_dump_path = str(paths["database_dump"])
        manifest.managed_files_archive_path = str(paths["managed_files"])
        manifest.media_archive_path = str(paths["media_files"])
        manifest.config_export_path = str(paths["published_configuration"])
        manifest.audit_export_path = str(paths["audit_events"])
        manifest.sha256_manifest = sha256_manifest
        manifest.state = BackupManifest.State.COMPLETED
        manifest.finished_at = timezone.now()
        manifest.save(
            update_fields=[
                "database_dump_path",
                "managed_files_archive_path",
                "media_archive_path",
                "config_export_path",
                "audit_export_path",
                "sha256_manifest",
                "state",
                "finished_at",
            ]
        )
    except Exception as exc:
        manifest.state = BackupManifest.State.FAILED
        manifest.finished_at = timezone.now()
        manifest.failure_message = str(exc)[:2000]
        manifest.save(update_fields=["state", "finished_at", "failure_message"])
        raise

    return manifest


def run_pg_dump(destination: Path):
    db_config = connections["default"].settings_dict
    if db_config["ENGINE"] != "django.db.backends.postgresql":
        raise BackupError("PostgreSQL backups require django.db.backends.postgresql.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--file",
        str(destination),
    ]
    if db_config.get("HOST"):
        command.extend(["--host", str(db_config["HOST"])])
    if db_config.get("PORT"):
        command.extend(["--port", str(db_config["PORT"])])
    if db_config.get("USER"):
        command.extend(["--username", str(db_config["USER"])])
    command.append(str(db_config["NAME"]))

    env = os.environ.copy()
    if db_config.get("PASSWORD"):
        env["PGPASSWORD"] = str(db_config["PASSWORD"])
    subprocess.run(command, env=env, check=True)


def _generate_backup_id():
    timestamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def _validate_backup_id(backup_id: str):
    backup_id = str(backup_id).strip()
    if not backup_id or not BACKUP_ID_RE.fullmatch(backup_id):
        raise BackupError(
            "Backup id must start with a letter or number and may contain only "
            "letters, numbers, dots, colons, dashes, and underscores."
        )
    return backup_id


def _write_archive(source_root: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz") as archive:
        if not source_root.exists():
            return
        for path in sorted(source_root.rglob("*")):
            archive.add(path, arcname=path.relative_to(source_root).as_posix(), recursive=False)


def _write_published_configuration(destination: Path):
    configuration = ConfigurationVersion.objects.order_by("-version").first()
    if configuration is None:
        payload = {"version": None, "published_at": None, "data": None}
    else:
        payload = {
            "id": configuration.pk,
            "version": configuration.version,
            "published_at": configuration.published_at,
            "published_by_id": configuration.published_by_id,
            "data": configuration.data,
        }
    _write_json(destination, payload)


def _write_audit_export(destination: Path):
    events = []
    queryset = AuditEvent.objects.select_related("actor").order_by("created_at", "id")
    for event in queryset.iterator(chunk_size=500):
        events.append(
            {
                "id": event.pk,
                "actor_id": event.actor_id,
                "actor_username": event.actor.username if event.actor_id else "",
                "action": event.action,
                "object_type": event.object_type,
                "object_id": event.object_id,
                "before": event.before,
                "after": event.after,
                "request_id": event.request_id,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "created_at": event.created_at,
            }
        )
    _write_json(destination, {"events": events})


def _write_env_fingerprint(destination: Path, env_file: Path):
    file_values = {}
    if env_file.exists():
        file_values = {key: value for key, value in dotenv_values(env_file).items() if key}

    keys = set(DEFAULT_ENV_KEYS) | set(file_values)
    values = {key: os.environ.get(key, file_values.get(key, "")) for key in keys}
    payload = {key: _fingerprint_env_value(key, values[key]) for key in sorted(keys)}
    _write_json(destination, payload)


def _fingerprint_env_value(key: str, value):
    value = "" if value is None else str(value)
    if _is_secret_key(key):
        return {
            "classification": "secret",
            "value_sha256": _sha256_text(value),
            "value_length": len(value),
        }
    sanitized_value = _sanitize_plain_value(key, value)
    return {
        "classification": "plain",
        "value": sanitized_value,
        "value_sha256": _sha256_text(sanitized_value),
    }


def _is_secret_key(key: str):
    normalized = key.upper()
    return any(part in normalized for part in SECRET_KEY_PARTS)


def _sanitize_plain_value(key: str, value: str):
    if not key.upper().endswith("URL"):
        return value
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return value
    netloc = parsed.hostname or ""
    if parsed.username:
        netloc = parsed.username + (":***" if parsed.password else "") + "@" + netloc
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    query = urlencode(
        sorted(
            (
                parameter,
                "***" if _is_secret_key(parameter) else parameter_value,
            )
            for parameter, parameter_value in parse_qsl(parsed.query, keep_blank_values=True)
        ),
        safe="*",
    )
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, query, parsed.fragment))


def _build_sha256_manifest(backup_id: str, paths: dict[str, Path]):
    return {
        "backup_id": backup_id,
        "generated_at": timezone.now().isoformat(),
        "files": {
            label: {
                "path": str(path),
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for label, path in sorted(paths.items())
        },
    }


def _sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_json(destination: Path, payload):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, cls=DjangoJSONEncoder, indent=2, sort_keys=True)
        handle.write("\n")


def _ensure_child_path(path: Path, parent: Path):
    try:
        relative_path = path.relative_to(parent)
    except ValueError as exc:
        raise BackupError(f"Backup path {path} is outside backup root {parent}.") from exc
    if relative_path == Path("."):
        raise BackupError(f"Backup path {path} must be a strict child of backup root {parent}.")


import hashlib
import importlib
import importlib.util
import json
import tarfile
from pathlib import Path

import pytest

from apps.audit.models import AuditEvent
from apps.backups.services import BackupError, create_backup
from apps.config_registry.models import ConfigurationVersion


pytestmark = pytest.mark.django_db


def test_backup_manifest_records_paths_and_sha256_payloads(tmp_path, settings, monkeypatch):
    spec = importlib.util.find_spec("apps.backups.services")
    assert spec is not None, "apps.backups.services must provide backup creation"
    create_backup = importlib.import_module("apps.backups.services").create_backup

    managed_root = tmp_path / "managed"
    media_root = tmp_path / "media"
    backup_root = tmp_path / "backups"
    managed_root.mkdir()
    media_root.mkdir()
    (managed_root / "engineering" / "spec.txt").parent.mkdir()
    (managed_root / "engineering" / "spec.txt").write_text("ABS-42\n", encoding="utf-8")
    (media_root / "documents").mkdir()
    (media_root / "documents" / "revision.pdf").write_bytes(b"%PDF backup fixture")

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "APP_HOST=hub.internal.example",
                "SECRET_KEY=do-not-export-this",
                "POSTGRES_PASSWORD=also-secret",
            ]
        ),
        encoding="utf-8",
    )

    settings.BACKUP_ROOT = str(backup_root)
    settings.MANAGED_FILE_ROOT = str(managed_root)
    settings.MEDIA_ROOT = str(media_root)
    monkeypatch.setenv("APP_HOST", "hub.internal.example")
    monkeypatch.setenv("SECRET_KEY", "do-not-export-this")
    monkeypatch.setenv("POSTGRES_PASSWORD", "also-secret")

    ConfigurationVersion.objects.create(
        version=7,
        data={"object_types": [{"key": "resin", "label": "Resin", "fields": []}]},
    )
    AuditEvent.objects.create(
        action="backup.test",
        object_type="resin",
        object_id="R-100",
        after={"status": "ok"},
    )

    dump_destinations = []

    def fake_database_dump(destination: Path):
        dump_destinations.append(destination)
        destination.write_text("postgres dump\n", encoding="utf-8")

    manifest = create_backup(
        backup_id="backup-test",
        backup_root=backup_root,
        managed_root=managed_root,
        media_root=media_root,
        env_file=env_file,
        database_dump_runner=fake_database_dump,
    )

    assert manifest.backup_id == "backup-test"
    assert manifest.state == "completed"
    assert manifest.finished_at is not None
    assert dump_destinations == [Path(manifest.database_dump_path)]

    paths = {
        "database_dump": Path(manifest.database_dump_path),
        "managed_files": Path(manifest.managed_files_archive_path),
        "media_files": Path(manifest.media_archive_path),
        "published_configuration": Path(manifest.config_export_path),
        "audit_events": Path(manifest.audit_export_path),
    }
    for path in paths.values():
        assert path.exists()

    with tarfile.open(paths["managed_files"], "r:gz") as archive:
        assert "engineering/spec.txt" in archive.getnames()
    with tarfile.open(paths["media_files"], "r:gz") as archive:
        assert "documents/revision.pdf" in archive.getnames()

    exported_config = json.loads(paths["published_configuration"].read_text(encoding="utf-8"))
    assert exported_config["version"] == 7
    assert exported_config["data"]["object_types"][0]["key"] == "resin"

    exported_audit = json.loads(paths["audit_events"].read_text(encoding="utf-8"))
    assert exported_audit["events"][0]["action"] == "backup.test"

    sha_manifest = manifest.sha256_manifest
    assert set(paths) <= set(sha_manifest["files"])
    for label, path in paths.items():
        assert sha_manifest["files"][label]["path"] == str(path)
        assert sha_manifest["files"][label]["sha256"] == _sha256(path)
        assert sha_manifest["files"][label]["size_bytes"] == path.stat().st_size

    env_fingerprint_path = Path(sha_manifest["files"]["env_fingerprint"]["path"])
    env_fingerprint = json.loads(env_fingerprint_path.read_text(encoding="utf-8"))
    assert env_fingerprint["APP_HOST"]["classification"] == "plain"
    assert env_fingerprint["APP_HOST"]["value"] == "hub.internal.example"
    assert env_fingerprint["SECRET_KEY"]["classification"] == "secret"
    assert env_fingerprint["POSTGRES_PASSWORD"]["classification"] == "secret"
    serialized_fingerprint = json.dumps(env_fingerprint)
    assert "do-not-export-this" not in serialized_fingerprint
    assert "also-secret" not in serialized_fingerprint


@pytest.mark.parametrize("backup_id", [".", "..", "-starts-with-dash", "_starts_with_underscore"])
def test_backup_rejects_unsafe_backup_ids(tmp_path, settings, backup_id):
    backup_root = tmp_path / "backups"
    settings.BACKUP_ROOT = str(backup_root)

    with pytest.raises(BackupError):
        create_backup(
            backup_id=backup_id,
            backup_root=backup_root,
            managed_root=tmp_path / "managed",
            media_root=tmp_path / "media",
            database_dump_runner=lambda destination: destination.write_text(
                "postgres dump\n",
                encoding="utf-8",
            ),
        )

    assert not backup_root.exists()


def test_backup_redacts_secret_url_query_values(tmp_path, settings, monkeypatch):
    managed_root = tmp_path / "managed"
    media_root = tmp_path / "media"
    backup_root = tmp_path / "backups"
    env_file = tmp_path / ".env"
    managed_root.mkdir()
    media_root.mkdir()
    env_file.write_text(
        "SERVICE_URL=https://host/path?token=secret&mode=safe&api_key=hidden\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SERVICE_URL", "https://host/path?token=secret&mode=safe&api_key=hidden")
    settings.BACKUP_ROOT = str(backup_root)
    settings.MANAGED_FILE_ROOT = str(managed_root)
    settings.MEDIA_ROOT = str(media_root)

    manifest = create_backup(
        backup_id="backup-safe-url",
        backup_root=backup_root,
        managed_root=managed_root,
        media_root=media_root,
        env_file=env_file,
        database_dump_runner=lambda destination: destination.write_text(
            "postgres dump\n",
            encoding="utf-8",
        ),
    )

    env_fingerprint_path = Path(manifest.sha256_manifest["files"]["env_fingerprint"]["path"])
    env_fingerprint = json.loads(env_fingerprint_path.read_text(encoding="utf-8"))
    service_url = env_fingerprint["SERVICE_URL"]["value"]
    assert service_url == "https://host/path?api_key=***&mode=safe&token=***"
    assert "secret" not in json.dumps(env_fingerprint["SERVICE_URL"])
    assert "hidden" not in json.dumps(env_fingerprint["SERVICE_URL"])


def _sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

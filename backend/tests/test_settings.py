# ===
# File Summary
# Path: backend\tests\test_settings.py
# Type: python
# Purpose: Backend test suite validating domain invariants and API behavior.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: test_allowed_hosts_include_app_host, test_celery_beat_schedules_backup_and_managed_folder_scans
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

def test_allowed_hosts_include_app_host(settings):
    assert "plastic-hub.local" in settings.ALLOWED_HOSTS


def test_celery_beat_schedules_backup_and_managed_folder_scans(settings):
    assert settings.CELERY_BEAT_SCHEDULE["nightly-backup-at-0200"]["task"] == (
        "apps.backups.tasks.create_scheduled_backup"
    )
    assert settings.CELERY_BEAT_SCHEDULE["scan-managed-folders-every-15-minutes"]["task"] == (
        "apps.folders.tasks.scan_managed_folders"
    )


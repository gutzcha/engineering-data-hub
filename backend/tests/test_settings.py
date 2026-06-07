def test_allowed_hosts_include_app_host(settings):
    assert "plastic-hub.local" in settings.ALLOWED_HOSTS


def test_celery_beat_schedules_backup_and_managed_folder_scans(settings):
    assert settings.CELERY_BEAT_SCHEDULE["nightly-backup-at-0200"]["task"] == (
        "apps.backups.tasks.create_scheduled_backup"
    )
    assert settings.CELERY_BEAT_SCHEDULE["scan-managed-folders-every-15-minutes"]["task"] == (
        "apps.folders.tasks.scan_managed_folders"
    )
